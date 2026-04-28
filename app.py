import os
import json
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from datetime import datetime, timedelta
import logging
import asyncio
from playwright.async_api import async_playwright

# ... (Configuración inicial igual al anterior) ...

async def scrape_profile(page, username, csrf=''):
    """
    Extrae info detallada usando el endpoint interno de IG y calculando métricas de Reels.
    """
    try:
        # User-Agent de móvil suele ser más permisivo para web_profile_info
        url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
        
        headers = {
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
            'Referer': f'https://www.instagram.com/{username}/',
            'X-CSRFToken': csrf,
        }

        resp = await page.request.get(url, headers=headers)

        if resp.status == 404:
            return {'success': False, 'error': 'Usuario no existe'}
        if not resp.ok:
            return {'success': False, 'error': f'Error IG: {resp.status}'}

        data = await resp.json()
        user = data.get('data', {}).get('user')
        
        if not user:
            return {'success': False, 'error': 'Perfil privado o restringido'}

        # Datos base
        followers = user.get('edge_followed_by', {}).get('count', 0)
        following = user.get('edge_follow', {}).get('count', 0)
        total_posts = user.get('edge_owner_to_timeline_media', {}).get('count', 0)
        
        # Filtrado de la última semana (Lunes a Domingo)
        start_ts, end_ts, week_label = get_last_week_range()
        edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
        
        reels_data = []
        for edge in edges:
            node = edge.get('node', {})
            ts = node.get('taken_at_timestamp', 0)
            
            # Verificamos que sea video/reel y esté en el rango de fechas
            if start_ts <= ts <= end_ts:
                is_video = node.get('is_video', False)
                if is_video:
                    reels_data.append({
                        'likes': node.get('edge_liked_by', {}).get('count', 0),
                        'comments': node.get('edge_media_to_comment', {}).get('count', 0),
                        'views': node.get('video_view_count', 0) or 0
                    })

        # Cálculos de métricas
        posts_week = len(reels_data)
        t_likes = sum(r['likes'] for r in reels_data)
        t_comments = sum(r['comments'] for r in reels_data)
        t_views = sum(r['views'] for r in reels_data)
        
        avg_v = round(t_views / posts_week, 0) if posts_week > 0 else 0
        # Engagement Rate: ((Likes + Comentarios) / Seguidores) * 100
        eng_rate = round(((t_likes + t_comments) / followers * 100), 2) if followers > 0 and posts_week > 0 else 0

        return {
            'success': True,
            'seguidores': followers,
            'following': following,
            'posts': total_posts,
            'bio': user.get('biography', ''),
            'posts_week': posts_week,
            'total_likes_week': t_likes,
            'total_comments_week': t_comments,
            'total_views_week': t_views,
            'avg_likes': round(t_likes / posts_week, 1) if posts_week > 0 else 0,
            'avg_comments': round(t_comments / posts_week, 1) if posts_week > 0 else 0,
            'avg_views': avg_v,
            'engagementRate': eng_rate,
            'week_label': week_label
        }
    except Exception as e:
        logger.error(f"Error scraping {username}: {str(e)}")
        return {'success': False, 'error': 'Error de conexión'}