"""QR SVG rendering with a lightweight default and an optional OpenCV backend."""
import io
import importlib.util
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def available():
    backend = getattr(settings, 'QR_BACKEND', 'auto')
    return ((backend in ('auto', 'qrcode') and importlib.util.find_spec('qrcode') is not None)
            or (backend in ('auto', 'opencv') and importlib.util.find_spec('cv2') is not None))


def opencv_svg(value):
    import cv2
    matrix = cv2.QRCodeEncoder_create().encode(value)
    size = matrix.shape[0] + 8
    # Include an explicit quiet zone and white background for reliable scanning.
    path = ''.join(f'M{x + 4},{y + 4}h1v1h-1z' for y, row in enumerate(matrix)
                   for x, pixel in enumerate(row) if pixel == 0)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
            f'width="{size * 6}" height="{size * 6}" shape-rendering="crispEdges">'
            '<rect width="100%" height="100%" fill="white"/>'
            f'<path d="{path}" fill="black"/></svg>').encode()


def render_svg(value):
    backend = getattr(settings, 'QR_BACKEND', 'auto')
    if backend in ('auto', 'qrcode') and importlib.util.find_spec('qrcode') is not None:
        import qrcode
        import qrcode.image.svg
        image = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathFillImage)
        stream = io.BytesIO()
        image.save(stream)
        return stream.getvalue()
    if backend in ('auto', 'opencv') and importlib.util.find_spec('cv2') is not None:
        return opencv_svg(value)
    raise ImproperlyConfigured('Install qrcode or the optional opencv-python-headless QR backend.')
