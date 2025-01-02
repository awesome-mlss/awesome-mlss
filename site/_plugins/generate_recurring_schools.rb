module Jekyll
  class MergeSchoolData < Generator
    safe true
    priority :highest

    def generate(site)

      # 1. Read in your data
      summerschools = site.data['summerschools'] || []
      archive       = site.data['archive'] || []
      all_items     = summerschools + archive

      # 2. Filter items: only those with a 'series' key
      series_items = all_items.select { |item| item['series'] }

      # 3. Group by 'series' name
      grouped_by_series = series_items.group_by { |item| item['series'] }

      # 4. Prepare the recurring structure
      recurring = []
      grouped_by_series.each do |series_name, events|
        # Sort items so the latest is first (assumes each item has 'year')
        sorted_events = events.sort_by { |e| e['year'] }.reverse

        # Use ID from the newest event, if that matters for your logic
        latest_id = sorted_events.first['id']

        # Build the data structure
        recurring << {
          'id'    => latest_id,            # ID of the newest event
          'series' => series_name,         # The name of the series
          'slug'  => slugify(series_name), # URL-friendly version of the series
          'items' => sorted_events         # All the items in that series
        }
      end

      # 5. Store it in site.data['recurringschools']
      site.data['recurringschools'] = recurring
    end

    private

    def slugify(str)
      str.downcase.strip
         .gsub(' ', '-')
         .gsub(/[^\w-]/, '')
    end
  end
end
