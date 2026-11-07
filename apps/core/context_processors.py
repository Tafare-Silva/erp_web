from decouple import config


def branding(request):
    name = config('BRAND_NAME', default='Blanjos Sistemas')
    short_name = config('BRAND_SHORT_NAME', default='')
    if not short_name:
        short_name = name.replace(' Sistemas', '').strip() or name
    return {
        'brand_name': name,
        'brand_short_name': short_name,
        'brand_tagline': config('BRAND_TAGLINE', default='Gestão Inteligente'),
        'brand_logo_url': config('BRAND_LOGO_URL', default=''),
        'brand_color': config('BRAND_COLOR', default='#0F1E36'),
    }
