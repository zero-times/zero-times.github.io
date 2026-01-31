#!/usr/bin/env python3
"""
Brazil News Collector
Collects trending news from Brazil and creates a daily news post for Jekyll blog
"""

import os
import sys
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import json
import urllib.parse

def get_brazilian_news():
    """Collect news from major Brazilian sources"""
    news_sources = [
        {
            'name': 'G1',
            'url': 'https://g1.globo.com',
            'api': 'https://g1.globo.com/rss/g1/'
        },
        {
            'name': 'UOL',
            'url': 'https://www.uol.com.br',
            'api': 'https://rss.uol.com.br/feed/noticias.xml'
        },
        {
            'name': 'Estadão',
            'url': 'https://estadao.com.br',
            'api': 'https://conteudo.estadao.com.br/rss/ultimas-noticias.xml'
        },
        {
            'name': 'Folha de S.Paulo',
            'url': 'https://www.folha.uol.com.br',
            'api': 'https://feeds.folha.uol.com.br/folha/ultimas90.xml'
        }
    ]
    
    all_news = []
    
    for source in news_sources:
        try:
            # Try RSS feed first
            if 'api' in source:
                response = requests.get(source['api'], timeout=10)
                if response.status_code == 200:
                    from xml.etree import ElementTree as ET
                    rss_content = response.text
                    
                    # Parse RSS
                    root = ET.fromstring(rss_content)
                    items = root.findall('.//item')
                    
                    for item in items[:5]:  # Take only top 5 articles
                        title_elem = item.find('title')
                        desc_elem = item.find('description')
                        link_elem = item.find('link')
                        pubdate_elem = item.find('pubDate')
                        
                        if title_elem is not None:
                            title = title_elem.text.strip()
                            desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ''
                            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ''
                            pubdate = pubdate_elem.text.strip() if pubdate_elem is not None and pubdate_elem.text else ''
                            
                            all_news.append({
                                'title': title,
                                'description': desc[:500],  # Limit description length
                                'link': link,
                                'source': source['name'],
                                'pubdate': pubdate
                            })
                        if len(all_news) >= 15:  # Limit total news items
                            break
            else:
                # Fallback to web scraping
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(source['url'], headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    # This is a simplified example - in reality, selectors would be specific to each site
                    articles = soup.find_all(['article', 'div'], class_=['widget--info', 'feed-post'])[:3]
                    
                    for article in articles:
                        title_elem = article.find(['h1', 'h2', 'h3', 'a'])
                        if title_elem:
                            title = title_elem.text.strip()
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            if link and not link.startswith('http'):
                                link = urllib.parse.urljoin(source['url'], link)
                            
                            all_news.append({
                                'title': title,
                                'description': 'Notícia coletada do portal ' + source['name'],
                                'link': link,
                                'source': source['name'],
                                'pubdate': datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
                            })
            
            if len(all_news) >= 15:  # Limit total news items
                break
                
        except Exception as e:
            print(f"Error collecting news from {source['name']}: {str(e)}")
            continue
    
    # Sort by most recent and return top 10
    return all_news[:10]

def create_news_post(news_items):
    """Create a Jekyll post with the collected news"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    post_filename = f"/Users/mac/Documents/GitHub/zero-times.github.io/_posts/{date_str}-daily-news-{datetime.now().strftime('%Y%m%d')}.md"
    
    # Create posts directory if it doesn't exist
    os.makedirs(os.path.dirname(post_filename), exist_ok=True)
    
    # Format the news items
    news_content = ""
    for i, item in enumerate(news_items, 1):
        news_content += f"\n{i}. **[{item['title']}]({item['link']})**\n"
        news_content += f"   - Fonte: {item['source']}\n"
        if item['description']:
            news_content += f"   - Resumo: {item['description']}\n"
        news_content += "\n"
    
    # Create the post content
    post_content = f"""---
layout: post
title: "Notícias Diárias do Brasil - {datetime.now().strftime('%d/%m/%Y')}"
date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
categories: noticias
lang: pt
---

# Notícias em Destaque no Brasil - {datetime.now().strftime('%d/%m/%Y')}

Segue um resumo das principais notícias coletadas automaticamente dos principais portais brasileiros hoje:

{news_content}

---
*Postagem automática gerada em {datetime.now().strftime('%d/%m/%Y às %H:%M')}*
"""
    
    # Write the post
    with open(post_filename, 'w', encoding='utf-8') as f:
        f.write(post_content)
    
    print(f"News post created: {post_filename}")
    return post_filename

def main():
    print("Collecting Brazilian news...")
    news_items = get_brazilian_news()
    
    if news_items:
        print(f"Collected {len(news_items)} news items")
        post_file = create_news_post(news_items)
        print(f"News post created successfully: {post_file}")
    else:
        print("No news items collected")

if __name__ == "__main__":
    main()