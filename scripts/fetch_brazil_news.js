/*
Brazil News Collector using Node.js
This script uses web scraping to collect news from Brazilian sources
*/

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { DateTime } = require('luxon');

// Function to simulate web fetching using shell commands
function fetchPage(url) {
    try {
        console.log(`Fetching: ${url}`);
        // Using curl to get the page content
        const result = execSync(`curl -s -L "${url}"`, { encoding: 'utf8', timeout: 15000 });
        return result;
    } catch (error) {
        console.error(`Error fetching ${url}:`, error.message);
        return null;
    }
}

function extractHeadlines(html, sourceName) {
    if (!html) return [];
    
    // Simple regex-based extraction (would be better with a proper HTML parser)
    const headlinePatterns = [
        /<h[1-3][^>]*class="[^"]*titulo[^"]*"[^>]*>([^<]{20,150})<\/h[1-3]>/gi,
        /<h[1-3][^>]*class="[^"]*title[^"]*"[^>]*>([^<]{20,150})<\/h[1-3]>/gi,
        /<a[^>]+title="([^"]{20,150})"[^>]*>.*?<\/a>/gi,
        /<a[^>]*>([^<]{30,150})<\/a>/gi,  // Simple anchor text extraction
    ];
    
    const headlines = new Set(); // Use Set to avoid duplicates
    
    for (const pattern of headlinePatterns) {
        let match;
        while ((match = pattern.exec(html)) !== null) {
            let title = match[1].trim();
            // Clean up the title
            title = title.replace(/&[a-z]+;/gi, ''); // Remove HTML entities
            title = title.replace(/\s+/g, ' ').substring(0, 150); // Normalize whitespace and limit length
            
            if (title.length > 25 && !title.toLowerCase().includes('vídeo') && 
                !title.toLowerCase().includes('anúncio') && !title.includes('...')) {
                headlines.add({
                    title: title,
                    source: sourceName,
                    link: '',
                    pubdate: DateTime.now().toFormat('dd/MM/yyyy HH:mm')
                });
                
                if (headlines.size >= 5) break; // Limit per source
            }
        }
        if (headlines.size >= 10) break; // Total limit
    }
    
    return Array.from(headlines);
}

function getBrazilianNews() {
    const newsSources = [
        { name: 'G1 Notícias', url: 'https://g1.globo.com/' },
        { name: 'UOL Notícias', url: 'https://www.uol.com.br/' },
        { name: 'Estadão', url: 'https://estadao.com.br/' },
        { name: 'Folha de S.Paulo', url: 'https://www.folha.uol.com.br/' }
    ];
    
    let allNews = [];
    
    for (const source of newsSources) {
        try {
            const content = fetchPage(source.url);
            if (content) {
                const headlines = extractHeadlines(content, source.name);
                allNews = allNews.concat(headlines.slice(0, 3)); // Take top 3 from each source
                
                if (allNews.length >= 10) {
                    allNews = allNews.slice(0, 10); // Limit to 10 total
                    break;
                }
            }
        } catch (error) {
            console.error(`Error processing ${source.name}:`, error.message);
        }
    }
    
    return allNews;
}

function createNewsPost(newsItems) {
    const dateStr = DateTime.now().toFormat('yyyy-MM-dd');
    const fileName = `${dateStr}-daily-news-${DateTime.now().toFormat('yyyyMMdd')}.md`;
    const postDir = path.join(__dirname, '..', '_posts');
    const filePath = path.join(postDir, fileName);
    
    // Create posts directory if it doesn't exist
    if (!fs.existsSync(postDir)) {
        fs.mkdirSync(postDir, { recursive: true });
    }
    
    // Format the news items
    let newsContent = '';
    if (newsItems && newsItems.length > 0) {
        newsItems.forEach((item, index) => {
            newsContent += `\n${index + 1}. **[${item.title}](${item.link || '#'})**\n`;
            newsContent += `   - Fonte: ${item.source}\n`;
            newsContent += `   - Data: ${item.pubdate}\n\n`;
        });
    } else {
        newsContent = '\nNenhuma notícia foi coletada automaticamente nesta data.\n';
    }
    
    // Create the post content
    const postContent = `---\nlayout: post\ntitle: "Notícias Diárias do Brasil - ${DateTime.now().toFormat('dd/MM/yyyy')}"\ndate: ${DateTime.now().toFormat('yyyy-MM-dd HH:mm:ss')}\ncategories: noticias\nlang: pt\n---\n\n# Notícias em Destaque no Brasil - ${DateTime.now().toFormat('dd/MM/yyyy')}\n\nSegue um resumo das principais notícias coletadas automaticamente dos principais portais brasileiros hoje:\n\n${newsContent}\n\n---\n*Postagem automática gerada em ${DateTime.now().toFormat('dd/MM/yyyy às HH:mm')}*\n`;
    
    // Write the post
    fs.writeFileSync(filePath, postContent, 'utf8');
    
    console.log(`News post created: ${filePath}`);
    
    // Attempt to commit the changes
    try {
        execSync('cd .. && git add . && git commit -m "Auto: Add daily Brazil news"', { stdio: 'pipe' });
        console.log('Changes committed to git');
    } catch (error) {
        console.log('Could not commit changes (may be no changes to commit)');
    }
    
    return filePath;
}

function main() {
    console.log('Collecting Brazilian news...');
    const newsItems = getBrazilianNews();
    
    if (newsItems.length > 0) {
        console.log(`Collected ${newsItems.length} news items`);
        const postFile = createNewsPost(newsItems);
        console.log(`News post created successfully: ${postFile}`);
    } else {
        console.log('No news items collected');
        const postFile = createNewsPost([]);
        console.log(`Empty news post created: ${postFile}`);
    }
}

// Run the main function
main();