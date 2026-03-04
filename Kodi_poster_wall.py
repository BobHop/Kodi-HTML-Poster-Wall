#============================ ABOUT ============================
#
# This script generates an HTML poster wall from an XML-exported
# Kodi database. It was coded by Claude Haiku 4.5 from my specs.
# It isn't supposed to replace a proper media interface like
# Kodi, Plex or Jellyfin – think of it as a quick way to display
# your collection. You still have to browse and open your media
# with an external player.
#
#============================ USAGE ============================
#
# 1. In Kodi, export your media database (only movies and TV
# shows are supported) to a local folder, as a single file. It
# will create a "videodb.xml" file, along with a handful of
# subfolders containing lots of images: you can deleted all of
# those images as they won't be used.
#
# 2. Place this .py script in the same folder as "videodb.xml"
# and run it. All the poster images will be downloaded (it can
# take a while so be patient!) in an "images" subfolder, then an
# "index.html" file will be created.
#
# 3. The poster images will be about 1000*1500 pixels large;
# that's huge, so use your favourite tool to batch-resize them
# all to something lighter (e.g. 400*600).
#
# 4. Open "index.html" in a web browser and enjoy your library
# presented in a clean responsive grid, alphabetically sorted,
# grouped by folder and type (movies first, TV shows last).
# Clicking a poster opens a modal card with more info (title,
# year, genres, plot).
#
#===============================================================

import xml.etree.ElementTree as ET
import os
import requests
from urllib.parse import urlparse
from pathlib import Path
import unicodedata
import re

def normalize_for_sort(text):
    """Normalise le texte pour un tri correct avec accents"""
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn').lower()

def sanitize_filename(filename):
    """Nettoie un nom de fichier"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.replace('&apos;', "'").replace('&amp;', '&').replace('&quot;', '"')
    return filename.strip()

def get_folder_name(path):
    """Extrait le nom du dossier parent"""
    path = path.rstrip('/\\')
    parts = path.replace('\\', '/').split('/')
    for part in reversed(parts):
        if part.strip():
            return part
    return "Autres"

def download_image(url, title):
    """Télécharge une image et la renomme"""
    os.makedirs('_images', exist_ok=True)
    
    try:
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1] or '.jpg'
        
        safe_title = sanitize_filename(title)
        filename = f"{safe_title}{ext}"
        filepath = os.path.join('_images', filename)
        
        if not os.path.exists(filepath):
            print(f"  ⬇️  Téléchargement: {title}...", end='', flush=True)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(" ✓")
        else:
            print(f"  ✓ Déjà présent: {title}")
        
        return filename
    except Exception as e:
        print(f" ✗ Erreur: {e}")
        return None

def parse_xml(filename):
    """Parse le fichier XML"""
    print(f"\n📂 Lecture du fichier {filename}...")
    tree = ET.parse(filename)
    root = tree.getroot()
    
    media_list = []
    
    # Traite les films
    for movie in root.findall('movie'):
        title = movie.findtext('title', 'Sans titre').replace('&apos;', "'")
        year = movie.findtext('year', 'N/A')
        path = movie.findtext('path', '')
        filenameandpath = movie.findtext('filenameandpath', '')
        plot = movie.findtext('plot', '').replace('&quot;', '"').replace('&apos;', "'")
        genres = [g.text for g in movie.findall('genre')]
        poster_url = movie.findtext('art/poster', '')
        
        # Tri par nom de fichier
        sort_key = normalize_for_sort(os.path.basename(filenameandpath)) if filenameandpath else normalize_for_sort(title)
        
        media_list.append({
            'type': 'movie',
            'title': title,
            'year': year,
            'path': path,
            'folder': get_folder_name(path),
            'plot': plot,
            'genres': genres,
            'poster_url': poster_url,
            'sort_key': sort_key
        })
    
    # Traite les séries
    for tvshow in root.findall('tvshow'):
        title = tvshow.findtext('title', 'Sans titre').replace('&apos;', "'")
        year = tvshow.findtext('year', 'N/A')
        plot = tvshow.findtext('plot', '').replace('&quot;', '"').replace('&apos;', "'")
        genres = [g.text for g in tvshow.findall('genre')]
        poster_url = tvshow.findtext('art/poster', '')
        
        media_list.append({
            'type': 'tvshow',
            'title': title,
            'year': year,
            'path': '',
            'folder': 'Séries',
            'plot': plot,
            'genres': genres,
            'poster_url': poster_url,
            'sort_key': normalize_for_sort(title)
        })
    
    print(f"✓ {len(media_list)} média(s) trouvé(s)")
    return media_list

def generate_html(media_list):
    """Génère le fichier HTML"""
    
    print(f"\n🖼️  Téléchargement des images...")
    # Télécharge les images et met à jour les chemins
    for media in media_list:
        if media['poster_url']:
            local_filename = download_image(media['poster_url'], media['title'])
            media['poster_path'] = f"./_images/{local_filename}" if local_filename else media['poster_url']
        else:
            media['poster_path'] = None
    
    print(f"\n📋 Tri et groupement...")
    # Trie par dossier puis par titre/filename
    media_list.sort(key=lambda x: (x['folder'], x['sort_key']))
    
    # Groupe par dossier
    groups = {}
    for media in media_list:
        folder = media['folder']
        if folder not in groups:
            groups[folder] = []
        groups[folder].append(media)
    
    print(f"✓ {len(groups)} section(s) créée(s)")
    
    print(f"\n🎨 Génération du HTML...")
    # Crée le HTML
    html = '''<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Médiathèque</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%);
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            padding: 40px 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .section-title {
            font-size: 24px;
            font-weight: 600;
            margin: 50px 0 20px 0;
            color: #ffffff;
            letter-spacing: 0.5px;
        }
        
        .section-title:first-of-type {
            margin-top: 0;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .poster-item {
            position: relative;
            cursor: pointer;
            border-radius: 8px;
            overflow: hidden;
            transition: all 0.3s ease;
            aspect-ratio: 2/3;
            background: #2a2a2a;
        }
        
        .poster-item img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        
        .poster-item:hover {
            transform: scale(1.05);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
        }
        
        .poster-item.active {
            box-shadow: 0 0 0 4px #ff6b35, 0 8px 24px rgba(255, 107, 53, 0.4);
            transform: scale(1.05);
        }
        
        /* Modal */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal-overlay.active {
            display: flex;
        }
        
        .modal {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 30px;
            max-width: 700px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.9);
        }
        
        .modal-content {
            display: flex;
            gap: 30px;
        }
        
        .modal-poster {
            flex-shrink: 0;
            width: 200px;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .modal-poster img {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .modal-info {
            flex: 1;
        }
        
        .modal-title {
            font-size: 28px;
            font-weight: 700;
            margin-bottom: 10px;
            color: #ffffff;
        }
        
        .modal-year {
            font-size: 16px;
            color: #a0a0a0;
            margin-bottom: 20px;
        }
        
        .modal-genres {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 20px;
        }
        
        .genre-tag {
            background: #2a2a2a;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            color: #e0e0e0;
            border: 1px solid #3a3a3a;
        }
        
        .modal-plot {
            font-size: 15px;
            line-height: 1.6;
            color: #c0c0c0;
        }
        
        /* Responsive */
        @media (max-width: 1200px) {
            .grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: repeat(3, 1fr);
                gap: 12px;
            }
            
            body {
                padding: 20px 10px;
            }
            
            .section-title {
                font-size: 20px;
                margin: 30px 0 15px 0;
            }
            
            .modal {
                padding: 20px;
            }
            
            .modal-content {
                flex-direction: column;
                gap: 20px;
            }
            
            .modal-poster {
                display: none;
            }
            
            .modal-title {
                font-size: 22px;
            }
        }
        
        @media (max-width: 480px) {
            .grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="container">
'''
    
    # Ajoute les sections
    for folder in groups.keys():
        html += f'        <h2 class="section-title">{folder}</h2>\n'
        html += '        <div class="grid">\n'
        
        for media in groups[folder]:
            if media['poster_path']:
                # Échappe les caractères spéciaux pour les attributs HTML
                title_escaped = media['title'].replace('"', '&quot;')
                plot_escaped = media['plot'].replace('"', '&quot;')
                genres_escaped = ', '.join(media['genres']).replace('"', '&quot;')
                
                html += f'''            <div class="poster-item" data-title="{title_escaped}" data-year="{media['year']}" data-genres="{genres_escaped}" data-plot="{plot_escaped}" data-poster="{media['poster_path']}">
                <img loading="lazy" src="{media['poster_path']}" alt="{title_escaped}">
            </div>\n'''
        
        html += '        </div>\n'
    
    html += '''    </div>
    
    <div class="modal-overlay" id="modalOverlay">
        <div class="modal">
            <div class="modal-content">
                <div class="modal-poster" id="modalPoster"></div>
                <div class="modal-info">
                    <h2 class="modal-title" id="modalTitle"></h2>
                    <p class="modal-year" id="modalYear"></p>
                    <div class="modal-genres" id="modalGenres"></div>
                    <p class="modal-plot" id="modalPlot"></p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const posterItems = document.querySelectorAll('.poster-item');
        const modalOverlay = document.getElementById('modalOverlay');
        const modal = document.querySelector('.modal');
        
        posterItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                
                // Retire la classe active des autres
                posterItems.forEach(p => p.classList.remove('active'));
                item.classList.add('active');
                
                // Rempli le modal
                const title = item.dataset.title;
                const year = item.dataset.year;
                const genres = item.dataset.genres.split(', ');
                const plot = item.dataset.plot;
                const poster = item.dataset.poster;
                
                document.getElementById('modalTitle').textContent = title;
                document.getElementById('modalYear').textContent = year;
                
                const genresDiv = document.getElementById('modalGenres');
                genresDiv.innerHTML = genres.map(g => `<span class="genre-tag">${g.trim()}</span>`).join('');
                
                document.getElementById('modalPlot').textContent = plot;
                
                const posterDiv = document.getElementById('modalPoster');
                if (poster) {
                    posterDiv.innerHTML = `<img src="${poster}" alt="${title}">`;
                }
                
                modalOverlay.classList.add('active');
            });
        });
        
        // Ferme le modal au clic en dehors
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                modalOverlay.classList.remove('active');
                posterItems.forEach(p => p.classList.remove('active'));
            }
        });
    </script>
</body>
</html>'''
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✓ Fichier index.html généré avec succès !")

if __name__ == '__main__':
    try:
        media_list = parse_xml('videodb.xml')
        generate_html(media_list)
        print("\n" + "="*50)
        print("✨ Terminé ! Ouvre index.html dans ton navigateur")
        print("="*50)
    except FileNotFoundError:
        print("❌ Erreur : le fichier videodb.xml n'a pas été trouvé")
    except Exception as e:
        print(f"❌ Erreur : {e}")
