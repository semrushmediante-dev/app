const express = require('express');
const cors = require('cors');
const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

// Usar plugin de stealth para evitar detección
puppeteer.use(StealthPlugin());

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Base de datos local (JSON)
const DB_FILE = path.join(__dirname, 'data.json');

function loadData() {
    try {
        if (fs.existsSync(DB_FILE)) {
            return JSON.parse(fs.readFileSync(DB_FILE, 'utf8'));
        }
    } catch (error) {
        console.error('Error loading data:', error);
    }
    return { accounts: [], history: [] };
}

function saveData(data) {
    fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2));
}

// Variable global para reutilizar el navegador
let browser = null;

async function getBrowser() {
    if (!browser) {
        console.log('🚀 Iniciando navegador Puppeteer...');
        try {
            browser = await puppeteer.launch({
                headless: 'new',
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            });
        } catch (error) {
            console.error('❌ Error al iniciar Puppeteer:', error.message);
            browser = null;
            throw error;
        }
    }
    return browser;
}

// Scraping de Instagram con Puppeteer
async function scrapeInstagramPuppeteer(username) {
    let page = null;
    try {
        console.log(`🔍 Scrapeando @${username} con Puppeteer...`);
        
        const browserInstance = await getBrowser();
        page = await browserInstance.newPage();
        
        // Simular un navegador real
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        
        const url = `https://www.instagram.com/${username}/?__a=1`;
        
        try {
            await page.goto(url, { waitUntil: 'networkidle2', timeout: 15000 });
        } catch (error) {
            console.log('⚠️ Timeout en carga, intentando extraer datos parciales...');
        }
        
        // Intentar obtener el JSON de la página
        const pageContent = await page.content();
        const $ = cheerio.load(pageContent);
        
        // Buscar datos en script tags
        let followers = null;
        let engagement = 0;
        
        $('script').each((i, elem) => {
            const text = $(elem).html();
            if (text && (text.includes('edge_followed_by') || text.includes('follower_count'))) {
                try {
                    // Intentar extraer JSON
                    const jsonMatch = text.match(/window\._sharedData\s*=\s*({.*?});</);
                    if (jsonMatch) {
                        const data = JSON.parse(jsonMatch[1]);
                        if (data.entry_data?.ProfilePage?.[0]?.graphql?.user) {
                            const user = data.entry_data.ProfilePage[0].graphql.user;
                            followers = user.edge_followed_by?.count || null;
                        }
                    }
                } catch (e) {
                    // Ignorar errores de parsing
                }
            }
        });
        
        // Si no encontramos datos, intentar otra estrategia
        if (!followers) {
            try {
                const preContent = $('pre').html();
                if (preContent) {
                    const preData = JSON.parse(preContent);
                    if (preData.user?.edge_followed_by?.count) {
                        followers = preData.user.edge_followed_by.count;
                    }
                }
            } catch (e) {
                // Ignorar
            }
        }
        
        await page.close();
        
        if (followers !== null) {
            console.log(`✅ ${username}: ${followers} seguidores obtenidos`);
            return {
                success: true,
                followers: followers,
                engagement: engagement,
                timestamp: new Date().toISOString().split('T')[0]
            };
        } else {
            console.log(`⚠️ No se encontraron datos para ${username}`);
            return {
                success: false,
                error: 'No se encontraron datos en la página',
                followers: null,
                engagement: null
            };
        }

    } catch (error) {
        console.log(`❌ Error en Puppeteer para @${username}: ${error.message}`);
        if (page) {
            try {
                await page.close();
            } catch (e) {
                // Ignorar error al cerrar
            }
        }
        return {
            success: false,
            error: error.message,
            followers: null,
            engagement: null
        };
    }
}

// Scraping alternativo con axios
async function scrapeInstagramAxios(username) {
    try {
        console.log(`🔍 Intentando con axios para @${username}...`);
        
        const url = `https://www.instagram.com/${username}/?__a=1&__d=dis`;
        
        const response = await axios.get(url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'es-ES,es;q=0.9',
                'Referer': 'https://www.instagram.com/'
            },
            timeout: 8000
        });

        if (response.data && response.data.user) {
            const user = response.data.user;
            const followers = user.edge_followed_by?.count || user.follower_count || null;
            
            if (followers) {
                console.log(`✅ ${username}: ${followers} seguidores (axios)`);
                return {
                    success: true,
                    followers: followers,
                    engagement: 0,
                    timestamp: new Date().toISOString().split('T')[0]
                };
            }
        }

        return {
            success: false,
            error: 'No se encontraron datos en la respuesta',
            followers: null,
            engagement: null
        };

    } catch (error) {
        console.log(`⚠️ Axios falló para @${username}: ${error.message}`);
        return {
            success: false,
            error: error.message,
            followers: null,
            engagement: null
        };
    }
}

// Función que intenta ambos métodos
async function scrapeInstagram(username) {
    console.log(`\n📱 Obteniendo datos de @${username}...`);
    
    // Primero intentar con axios (más rápido)
    const axiosResult = await scrapeInstagramAxios(username);
    if (axiosResult.success) {
        return axiosResult;
    }
    
    console.log('⏳ Axios no funcionó, intentando con Puppeteer...');
    
    // Si axios falla, intentar con Puppeteer
    const puppeteerResult = await scrapeInstagramPuppeteer(username);
    return puppeteerResult;
}

// API: Importar cuentas desde CSV
app.post('/api/import-csv', (req, res) => {
    try {
        const { csvData } = req.body;
        const lines = csvData.trim().split('\n');
        const newAccounts = [];

        const data = loadData();
        
        for (let i = 1; i < lines.length; i++) {
            const parts = lines[i].split(',');
            if (parts.length < 3) continue;

            const usuario = parts[0].trim().replace(/"/g, '');
            const encargada = parts[1].trim().replace(/"/g, '');
            const url = parts[2].trim().replace(/"/g, '');

            if (!usuario || !encargada || !url) continue;

            if (!data.accounts.find(a => a.usuario === usuario)) {
                newAccounts.push({
                    id: Date.now() + i,
                    usuario: usuario,
                    encargada: encargada,
                    url: url,
                    seguidores: null,
                    engagementRate: null,
                    lastUpdate: null,
                    status: 'pending'
                });
            }
        }

        data.accounts.push(...newAccounts);
        saveData(data);

        res.json({
            success: true,
            message: `${newAccounts.length} cuentas importadas`,
            accounts: newAccounts
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// API: Obtener seguidores de una cuenta
app.post('/api/fetch-followers', async (req, res) => {
    try {
        const { usuario } = req.body;
        const data = loadData();
        const account = data.accounts.find(a => a.usuario === usuario);

        if (!account) {
            return res.status(404).json({ success: false, error: 'Cuenta no encontrada' });
        }

        // Obtener datos
        const result = await scrapeInstagram(usuario);
        
        if (result.success) {
            account.seguidores = result.followers;
            account.engagementRate = parseFloat(result.engagement);
            account.lastUpdate = result.timestamp;
            account.status = 'completed';

            // Agregar al historial
            data.history.push({
                usuario: usuario,
                seguidores: result.followers,
                engagementRate: result.engagement,
                fecha: result.timestamp
            });

            saveData(data);

            res.json({
                success: true,
                data: {
                    usuario: usuario,
                    seguidores: result.followers,
                    engagementRate: result.engagement,
                    timestamp: result.timestamp
                }
            });
        } else {
            account.status = 'failed';
            saveData(data);
            
            res.status(500).json({
                success: false,
                error: 'No se pudieron obtener los datos automáticamente. Actualiza manualmente.',
                details: result.error
            });
        }
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// API: Obtener todas las cuentas
app.get('/api/accounts', (req, res) => {
    try {
        const data = loadData();
        res.json({ success: true, accounts: data.accounts });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// API: Obtener historial
app.get('/api/history', (req, res) => {
    try {
        const data = loadData();
        res.json({ success: true, history: data.history });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// API: Actualizar seguidores manualmente
app.post('/api/update-followers', (req, res) => {
    try {
        const { usuario, seguidores, engagementRate } = req.body;
        const data = loadData();
        const account = data.accounts.find(a => a.usuario === usuario);

        if (!account) {
            return res.status(404).json({ success: false, error: 'Cuenta no encontrada' });
        }

        if (!seguidores || isNaN(seguidores) || seguidores < 0) {
            return res.status(400).json({ success: false, error: 'Número de seguidores inválido' });
        }

        const today = new Date().toISOString().split('T')[0];
        
        account.seguidores = parseInt(seguidores);
        account.engagementRate = engagementRate ? parseFloat(engagementRate) : (account.engagementRate || 0);
        account.lastUpdate = today;
        account.status = 'completed';

        data.history.push({
            usuario: usuario,
            seguidores: parseInt(seguidores),
            engagementRate: account.engagementRate,
            fecha: today
        });

        saveData(data);

        res.json({ 
            success: true, 
            message: `Datos de @${usuario} actualizados correctamente`,
            data: {
                usuario: usuario,
                seguidores: parseInt(seguidores),
                engagementRate: account.engagementRate,
                timestamp: today
            }
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// API: Eliminar cuenta
app.delete('/api/account/:usuario', (req, res) => {
    try {
        const { usuario } = req.params;
        const data = loadData();
        
        data.accounts = data.accounts.filter(a => a.usuario !== usuario);
        data.history = data.history.filter(h => h.usuario !== usuario);

        saveData(data);

        res.json({ success: true, message: 'Cuenta eliminada' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// API: Exportar CSV
app.get('/api/export-csv', (req, res) => {
    try {
        const data = loadData();
        
        let csv = 'Usuario,Encargada,URL,Seguidores,Engagement Rate (%),Última Actualización\n';
        data.accounts.forEach(account => {
            csv += `${account.usuario},${account.encargada},${account.url},${account.seguidores || 'N/A'},${account.engagementRate || 'N/A'},${account.lastUpdate || 'N/A'}\n`;
        });

        res.setHeader('Content-Type', 'text/csv');
        res.setHeader('Content-Disposition', 'attachment; filename="instagram_seguidores.csv"');
        res.send(csv);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// API: Limpiar datos
app.delete('/api/clear-all', (req, res) => {
    try {
        saveData({ accounts: [], history: [] });
        res.json({ success: true, message: 'Todos los datos han sido eliminados' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`\n🚀 Servidor corriendo en http://localhost:${PORT}`);
    console.log('📊 Abre http://localhost:3000 en tu navegador\n');
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n⏹️  Cerrando servidor...');
    if (browser) {
        await browser.close();
    }
    process.exit(0);
});
