content = open('django_app/core/settings.py').read()

# Add corsheaders to INSTALLED_APPS
content = content.replace(
    "'accounts',",
    "'corsheaders',\n    'accounts',"
)

# Add CorsMiddleware to top of MIDDLEWARE
content = content.replace(
    "'django.middleware.security.SecurityMiddleware',",
    "'corsheaders.middleware.CorsMiddleware',\n    'django.middleware.security.SecurityMiddleware',"
)

# Add CORS settings at the end
content += "\nCORS_ALLOW_ALL_ORIGINS = True\n"

open('django_app/core/settings.py', 'w').write(content)
print('Done - CORS settings added')