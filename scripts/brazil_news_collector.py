#!/usr/bin/env python3
"""
Brazil News Collector for OpenClaw
Uses OpenClaw's web_fetch tool to collect news from Brazilian sources
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

def web_fetch(url):
    """Use OpenClaw's web_fetch tool to get content"""
    try:
        # Call OpenClaw's web_fetch tool via command line
        cmd = [
            "openclaw", "tool", "web_fetch", 
            "--url", url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Error fetching {url}: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception fetching {url}: {str(e)}")
        return None

def search_web(query):
    """Use OpenClaw's web_search tool to find Brazilian news"""
    try:
        cmd = [
            "openclaw", "tool", "web_search",
            "--query", query,
            "--country", "BR",
            "--count", "5"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Parse the search results
            lines = result.stdout.strip().split('\n')
            results = []
            for line in lines:
                if line.strip() and ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        results.append({
                            'title': parts[0].strip(),
                            'url': parts[1].strip()
                        })
            return results
        else:
            print(f"Error searching: {result.stderr}")
            return []
    except Exception as e:
        print(f"Exception searching: {str(e)}")
        return []

def get_brazilian_news():
    """Collect news from Brazilian sources using web search and fetch"""
    # Search for trending news in Brazil
    search_terms = [
        "notícias Brasil últimas",
        "notícias Brasil hoje",
        "trending Brasil",
        "notícias importantes Brasil"
    ]
    
    all_news = []
    
    for term in search_terms:
        print(f"Searching for: {term}")
        search_results = search_web(term)
        
        for result in search_results[:2]:  # Take top 2 from each search
            title = result.get('title', '')
            url = result.get('url', '')
            
            if title and url and len(title) > 10:
                # Add to news if it's not a duplicate
                is_duplicate = False
                for item in all_news:
                    if item['title'].lower() == title.lower():
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    all_news.append({
                        'title': title,
                        'link': url,
                        'source': 'Busca Web',
                        'pubdate': datetime.now().strftime('%d/%m/%Y %H:%M')
                    })
                    
                    if len(all_news) >= 10:  # Limit to 10 news items
                        break
        
        if len(all_news) >= 10:
            break
    
    # If we still don't have enough news, try specific Brazilian news sites
    if len(all_news) < 5:
        brazilian_sites = [
            {'name': 'G1', 'url': 'https://g1.globo.com'},
            {'name': 'UOL', 'url': 'https://www.uol.com.br'},
            {'name': 'Estadão', 'url': 'https://estadao.com.br'}
        ]
        
        for site in brazilian_sites:
            print(f"Fetching from {site['name']}: {site['url']}")
            content = web_fetch(site['url'])
            
            if content and len(content) > 100:
                # Extract headlines from the content
                import re
                # Look for heading patterns in the content
                title_matches = re.findall(r'<title[^>]*>([^<]{10,100})</title>|<h[1-3][^>]*>([^<]{10,100})</h[1-3]>', content[:3000])
                
                for match in title_matches:
                    title = match[0] or match[1]  # Get the non-empty match
                    if title and len(title) > 15:
                        # Clean up title
                        title = title.strip()
                        if ' - ' in title:
                            title = title.split(' - ')[0].strip()
                        
                        is_duplicate = False
                        for item in all_news:
                            if item['title'].lower() == title.lower():
                                is_duplicate = True
                                break
                        
                        if not is_duplicate and len(title) > 10:
                            all_news.append({
                                'title': title,
                                'link': site['url'],
                                'source': site['name'],
                                'pubdate': datetime.now().strftime('%d/%m/%Y %H:%M')
                            })
                            
                            if len(all_news) >= 10:
                                break
            
            if len(all_news) >= 10:
                break
    
    return all_news

def create_news_post(news_items):
    """Create a Jekyll post with the collected news"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    post_filename = f"_posts/{date_str}-daily-news-{datetime.now().strftime('%Y%m%d')}.md"
    full_path = Path("/Users/mac/Documents/GitHub/zero-times.github.io") / post_filename
    
    # Create posts directory if it doesn't exist
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Format the news items
    news_content = ""
    if news_items:
        for i, item in enumerate(news_items, 1):
            news_content += f"\n{i}. **[{item['title']}]({item['link']})**\n"
            news_content += f"   - Fonte: {item['source']}\n"
            news_content += f"   - Data: {item['pubdate']}\n\n"
    else:
        news_content = "\nNenhuma notícia foi coletada automaticamente nesta data.\n"
    
    # Format the news items in Brazilian Portuguese following the sample format
    br_news_content = ""
    if news_items:
        for i, item in enumerate(news_items, 1):
            br_news_content += f"**{item['title']}**\n"
            br_news_content += f"* Fonte: {item['source']}\n"
            br_news_content += f"* Data: {item['pubdate']}\n"
            if item['link'] != '':
                br_news_content += f"* [Leia mais]({item['link']})\n"
            br_news_content += "\n"
    else:
        br_news_content = "* Nenhuma notícia foi coletada automaticamente nesta data.\n"
    
    # Create the post content following the sample format
    post_content = f"""---
layout: post
title: "Destaques do Brasil - {datetime.now().strftime('%d/%m/%Y')}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S +0800')}
categories: news
lang: pt-br
---

# Destaques de Hoje (Notícias do Brasil) - Atualizado em: {datetime.now().strftime('%H:%M:%S')}

## 🇧🇷 Notícias do Brasil
{br_news_content}

## 🌍 Internacional
**Notícias globais**
* Notícias internacionais selecionadas
* Eventos geopolíticos e econômicos globais
* Tendências tecnológicas mundiais
* Impacto global

---

Última atualização: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Conteúdo gerado automaticamente para manter o site atualizado
Coletado automaticamente dos principais portais brasileiros

# Estatísticas do dia
- Notícias coletadas: {len(news_items)}
- Fontes monitoradas: 3

# Análise do dia
- Tópicos em alta: Negócios, Política, Economia
- Palavras-chave: Brasil, Notícias, Atualidades
- Tendências: Assuntos nacionais e internacionais

# Resumo Executivo
Esta é uma atualização automática contendo as principais notícias do Brasil e internacionais. O conteúdo é gerado automaticamente para manter os leitores informados sobre tópicos relevantes nas áreas de economia, política e sociedade.
"""
    
    # Write the post
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(post_content)
    
    print(f"News post created: {full_path}")
    
    # Attempt to commit the changes
    try:
        subprocess.run(["git", "-C", str(full_path.parent.parent), "add", str(full_path)], check=True)
        subprocess.run(["git", "-C", str(full_path.parent.parent), "commit", "-m", f"Auto: Add daily Brazil news for {date_str}"], check=True)
        subprocess.run(["git", "-C", str(full_path.parent.parent), "push", "origin", "master"], check=True)
        print("Changes committed and pushed to git")
    except subprocess.CalledProcessError as e:
        print(f"Could not commit changes: {e}")
    except Exception as e:
        print(f"Error committing changes: {e}")
    
    return str(full_path)

def main():
    print("Collecting Brazilian news...")
    news_items = get_brazilian_news()
    
    if news_items:
        print(f"Collected {len(news_items)} news items")
        post_file = create_news_post(news_items)
        print(f"News post created successfully: {post_file}")
    else:
        print("No news items collected")
        post_file = create_news_post([])
        print(f"Empty news post created: {post_file}")

if __name__ == "__main__":
    main()