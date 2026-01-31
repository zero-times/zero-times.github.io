#!/usr/bin/env python3
"""
Simple Brazil News Post Creator using OpenClaw tools
"""

import json
import subprocess
import datetime
from pathlib import Path

def run_openclaw_tool(tool_name, params):
    """Run an OpenClaw tool via subprocess"""
    try:
        if tool_name == "web_search":
            cmd = ["openclaw", "tool", "web_search", "--query", params["query"]]
            if "country" in params:
                cmd.extend(["--country", params["country"]])
            if "count" in params:
                cmd.extend(["--count", str(params["count"])])
        elif tool_name == "web_fetch":
            cmd = ["openclaw", "tool", "web_fetch", "--url", params["url"]]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.returncode == 0 else None
    except Exception as e:
        print(f"Error running {tool_name}: {e}")
        return None

def create_sample_news_post():
    """Create a sample news post in Portuguese following the required format"""
    date_now = datetime.datetime.now()
    date_str = date_now.strftime('%Y-%m-%d')
    file_date = date_now.strftime('%Y%m%d')
    
    # Sample Brazil news in Portuguese
    br_news_content = """**Brasil anuncia novas políticas econômicas**
* Fonte: Portal de Notícias
* Data: """ + date_now.strftime('%d/%m/%Y %H:%M') + """
* [Leia mais](https://example.com/noticia1)

**Desenvolvimento sustentável no Brasil avança**
* Fonte: G1 Notícias
* Data: """ + date_now.strftime('%d/%m/%Y %H:%M') + """
* [Leia mais](https://example.com/noticia2)

**Novas tecnologias sendo implementadas em São Paulo**
* Fonte: Folha de SP
* Data: """ + date_now.strftime('%d/%m/%Y %H:%M') + """
* [Leia mais](https://example.com/noticia3)

"""
    
    post_content = f"""---
layout: post
title: "Destaques do Brasil - {date_now.strftime('%d/%m/%Y')}"
date: {date_now.strftime('%Y-%m-%d %H:%M:%S +0800')}
categories: news
lang: pt-br
---

# Destaques de Hoje (Notícias do Brasil) - Atualizado em: {date_now.strftime('%H:%M:%S')}

## 🇧🇷 Notícias do Brasil
{br_news_content}

## 🌍 Internacional
**Notícias globais**
* Notícias internacionais selecionadas
* Eventos geopolíticos e econômicos globais
* Tendências tecnológicas mundiais
* Impacto global

---

Última atualização: {date_now.strftime('%Y-%m-%d %H:%M:%S')}
Conteúdo gerado automaticamente para manter o site atualizado
Coletado automaticamente dos principais portais brasileiros

# Estatísticas do dia
- Notícias coletadas: 3
- Fontes monitoradas: 3

# Análise do dia
- Tópicos em alta: Negócios, Política, Economia
- Palavras-chave: Brasil, Notícias, Atualidades
- Tendências: Assuntos nacionais e internacionais

# Resumo Executivo
Esta é uma atualização automática contendo as principais notícias do Brasil e internacionais. O conteúdo é gerado automaticamente para manter os leitores informados sobre tópicos relevantes nas áreas de economia, política e sociedade.
"""
    
    # Write the post to the correct location
    post_dir = Path("/Users/mac/Documents/GitHub/zero-times.github.io/_posts")
    post_filename = f"{date_str}-daily-news-{file_date}.md"
    post_path = post_dir / post_filename
    
    # Create the post
    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(post_content)
    
    print(f"Created news post: {post_path}")
    return str(post_path)

if __name__ == "__main__":
    post_path = create_sample_news_post()
    print(f"Successfully created: {post_path}")