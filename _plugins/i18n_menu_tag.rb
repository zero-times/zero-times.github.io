module Jekyll
  class I18nMenuTag < Liquid::Tag
    def initialize(tag_name, markup, options)
      super
      @menu_type, @lang = markup.strip.split(',', 2).map(&:strip)
    end

    def render(context)
      site = context.registers[:site]
      page = context.environments.first['page']

      # Determine language from parameter, page, site config, or default to pt-br
      requested_lang = @lang || page['lang'] || site.config['default_lang'] || 'pt-br'
      lang = normalize_language_code(requested_lang)

      # Get menus
      menus_data = site.data['menus']
      menu_items = menus_data[@menu_type]

      return "Menu not found: #{@menu_type}" unless menu_items

      # Generate HTML for menu items with translated titles
      menu_html = ''
      menu_items.each do |item|
        title = get_translated_title(item['title'], lang)
        url = item['url']
        css_class = item['class'] || ''
        
        # Check if this is an external link
        external = item['external'] ? 'target="_blank"' : ''
        
        menu_html += "<li class=\"nav-item\">\n"
        menu_html += "  <a class=\"nav-link px-3 #{css_class}\" href=\"#{url}\" #{external}>#{title}</a>\n"
        menu_html += "</li>\n"
      end

      menu_html
    end

    private

    def get_translated_title(title_hash, lang)
      # Try the requested language first, then fall back to others
      title_hash[lang] || 
      title_hash['pt-br'] || 
      title_hash['en'] || 
      title_hash['zh'] || 
      title_hash.values.first ||
      'Untitled'
    end

    def normalize_language_code(lang)
      case lang
      when /^pt/, 'pt-br', 'pt_BR'
        'pt-br'
      when /^en/, 'en-us', 'en_US'
        'en'
      when /^zh/, 'zh-cn', 'zh_CN', 'cn'
        'zh'
      else
        'pt-br' # Default to Brazilian Portuguese
      end
    end
  end
end

Liquid::Template.register_tag('i18n_menu', Jekyll::I18nMenuTag)