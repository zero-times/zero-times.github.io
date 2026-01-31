#!/usr/bin/env python3
"""
Simple Brazil News Collector
Uses web scraping to collect news from Brazilian sources
"""

import os
import sys
from datetime import datetime
import subprocess
import json

def fetch_with_web_fetch(url):
    """Helper function to use OpenClaw's web_fetch tool"""
    try:
        # Using curl as a fallback to get raw content
        result = subprocess.run(['curl', '-s', url], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout
        return None
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return None

def get_brazilian_news():
    """Collect news from major Brazilian sources"""
    news_sources = [
        {
            'name': 'G1 Últimas Notícias',
            'url': 'https://g1.globo.com/'
        },
        {
            'name': 'UOL Notícias',
            'url': 'https://www.uol.com.br/'
        },
        {
            'name': 'Estadão',
            'url': 'https://estadao.com.br/'
        }
    ]
    
    all_news = []
    
    for source in news_sources:
        try:
            print(f"Fetching from {source['name']}...")
            content = fetch_with_web_fetch(source['url'])
            
            if content:
                # This is a simplified extraction - in a real implementation, 
                # we would parse the HTML properly to extract headlines
                import re
                
                # Look for headline patterns in the HTML
                # This is a basic pattern that looks for common headline structures
                title_patterns = [
                    r'<h[1-3][^>]*>([^<]{10,100})</h[1-3]>',  # Headings
                    r'<a[^>]+class="[^"]*title[^"]*"[^>]*>([^<]{10,100})</a>',  # Title links
                    r'<a[^>]+class="[^"]*headline[^"]*"[^>]*>([^<]{10,100})</a>',  # Headline links
                    r'<a[^>]*title="([^"]{10,100})"[^>]*>',  # Title attributes
                ]
                
                for pattern in title_patterns:
                    matches = re.findall(pattern, content[:10000])  # Only look at first 10k chars
                    for match in matches[:3]:  # Take first 3 matches
                        clean_match = match.strip()
                        if len(clean_match) > 15 and not any(x in clean_match.lower() for x in ['vídeo', 'vídeos', 'anúncio', 'publicidade']):
                            all_news.append({
                                'title': clean_match,
                                'description': f"Notícia coletada do portal {source['name']}",
                                'link': source['url'],
                                'source': source['name'],
                                'pubdate': datetime.now().strftime('%d/%m/%Y %H:%M')
                            })
                            if len(all_news) >= 10:  # Limit to 10 news items
                                break
                    if len(all_news) >= 10:
                        break
            
            if len(all_news) >= 10:  # Limit total news items
                break
                
        except Exception as e:
            print(f"Error collecting news from {source['name']}: {str(e)}")
            continue
    
    return all_news

def create_news_post(news_items):
    """Create a Jekyll post with the collected news"""
    date_str = datetime.now().strftime('%Y-%m-%d')
    post_filename = f"_posts/{date_str}-daily-news-{datetime.now().strftime('%Y%m%d')}.md"
    full_path = f"/Users/mac/Documents/GitHub/zero-times.github.io/{post_filename}"
    
    # Create posts directory if it doesn't exist
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Format the news items
    news_content = ""
    if news_items:
        for i, item in enumerate(news_items, 1):
            news_content += f"\n{i}. **[{item['title']}]({item['link']})**\n"
            news_content += f"   - Fonte: {item['source']}\n"
            if item['description']:
                news_content += f"   - Resumo: {item['description']}\n"
            news_content += "\n"
    else:
        news_content = "\nNenhuma notícia foi coletada automaticamente nesta data.\n"
    
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
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(post_content)
    
    print(f"News post created: {full_path}")
    return full_path

def main():
    print("Collecting Brazilian news...")
    news_items = get_brazilian_news()
    
    if news_items:
        print(f"Collected {len(news_items)} news items")
        post_file = create_news_post(news_items)
        print(f"News post created successfully: {post_file}")
        
        # Commit the new post
        try:
            subprocess.run(['cd /Users/mac/Documents/GitHub/zero-times.github.io && git add .'], shell=True)
            subprocess.run(['cd /Users/mac/Documents/GitHub/zero-times.github.io && git commit -m "Auto: Add daily Brazil news for {datetime.now().strftime("%Y-%m-%d")}"'], shell=True)
            print("Changes committed to git")
        except Exception as e:
            print(f"Could not commit changes: {str(e)}")
    else:
        print("No news items collected")
        # Still create an empty post to maintain consistency
        post_file = create_news_post([])
        print(f"Empty news post created: {post_file}")

if __name__ == "__main__":
    main()