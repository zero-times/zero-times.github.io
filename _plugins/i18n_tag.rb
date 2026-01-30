module Jekyll
  class I18nTag < Liquid::Tag
    def initialize(tag_name, markup, options)
      super
      @key = markup.strip
    end

    def render(context)
      site = context.registers[:site]
      page = context.environments.first['page']

      # Determine language from page, site config, or default to pt-br
      lang = page['lang'] || site.config['default_lang'] || 'pt-br'

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
        result = value[lang] || value[site.config['default_lang']] || value['en'] || value.values.first
        result.to_s
      elsif value.nil?
        "Translation missing: #{@key}"
      else
        value.to_s
      end
    end
  end
end

Liquid::Template.register_tag('t', Jekyll::I18nTag)