module Jekyll
  module I18nFilter
    def translate(input, lang = nil)
      # Get the site object
      site = @context.registers[:site]
      
      # Determine the language to use
      lang ||= site.config['default_lang'] || 'pt-br'
      
      # Get the translation data
      translations = site.data['translations']
      
      # Navigate to the requested translation
      keys = input.split('.')
      value = translations
      
      keys.each do |key|
        if value.is_a?(Hash)
          value = value[key]
        else
          value = nil
          break
        end
      end
      
      # Return the translation for the requested language, or fallback to default
      if value.is_a?(Hash)
        result = value[lang] || value[site.config['default_lang']] || value['en'] || value.values.first
        result || input
      else
        value || input
      end
    end
    
    # Shortcut alias
    alias t translate
  end
end

Liquid::Template.register_filter(Jekyll::I18nFilter)