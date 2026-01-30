module Jekyll
  class I18nTag < Liquid::Tag
    def initialize(tag_name, markup, options)
      super
      @key, @lang = markup.strip.split(',', 2).map(&:strip)
    end

    def render(context)
      site = context.registers[:site]
      page = context.environments.first['page']

      # Determine language from parameter, page, site config, or default to pt-br
      requested_lang = @lang || page['lang'] || site.config['default_lang'] || 'pt-br'
      
      # Normalize language codes
      lang = normalize_language_code(requested_lang)

      # Get translations
      translations = site.data['translations']
      keys = @key.split('.')

      # Navigate to the requested translation
      value = translations
      keys.each do |key|
        if value.is_a?(Hash)
          value = value[key]
        else
          value = nil
          break
        end
      end

      # Return the translation for the requested language, or fallback
      if value.is_a?(Hash)
        # Try requested language, then default language, then English, then any available
        result = value[lang] || 
                 value[site.config['default_lang']] || 
                 value['en'] || 
                 value['pt-br'] || 
                 value['zh'] || 
                 value.values.first
        result.to_s
      elsif value.nil?
        "Translation missing: #{@key} (#{lang})"
      else
        value.to_s
      end
    end

    private

    def normalize_language_code(lang)
      case lang
      when /^pt/, 'pt-br', 'pt_BR'
        'pt-br'
      when /^en/, 'en-us', 'en_US'
        'en'
      when /^zh/, 'zh-cn', 'zh_CN', 'cn'
        'zh'
      else
        lang
      end
    end
  end
end

Liquid::Template.register_tag('t', Jekyll::I18nTag)