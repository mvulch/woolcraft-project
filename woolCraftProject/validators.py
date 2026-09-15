from django import forms
from django.core.files.uploadedfile import UploadedFile

MAX_IMAGE_SIZE = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp')
USER_IMAGE_TRANSFORMATION = [{'width': 1600, 'height': 1600, 'crop': 'limit'}]

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput(attrs={'class': 'd-none', 'multiple': True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)] if data else []

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