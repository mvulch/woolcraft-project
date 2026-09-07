from django import forms
from django.core.files.uploadedfile import UploadedFile

MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp')

def validate_client_images(image):
    # if empty
    if not image:
        return image

    if isinstance(image, UploadedFile):
        if image.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError(f'Твърде голям файл. Максимален размер: {MAX_IMAGE_SIZE // (1024 * 1024)} MB.')

    content_type = getattr(image, 'content_type', None)
    if content_type is None:
        return image
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise forms.ValidationError('Непозволен формат. Изберете изображение във формат PNG, JPEG или WebP.')
    return image