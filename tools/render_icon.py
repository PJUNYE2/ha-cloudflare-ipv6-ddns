"""Render the simple geometric DDNS brand icon without external assets."""
from pathlib import Path

from PIL import Image, ImageDraw

image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)


def box(values):
    return tuple(value * 4 for value in values)


draw.rounded_rectangle(box((8, 8, 248, 248)), radius=224, fill="#102439")
draw.ellipse(box((40, 82, 102, 144)), fill="#f89a38")
draw.ellipse(box((69, 53, 161, 145)), fill="#f89a38")
draw.ellipse(box((142, 81, 210, 145)), fill="#f89a38")
draw.rectangle(box((70, 109, 181, 144)), fill="#f89a38")
for points in [[(62, 174), (185, 174), (166, 155)], [(194, 204), (71, 204), (90, 223)]]:
    draw.line([(x * 4, y * 4) for x, y in points], fill="#f5faff", width=52, joint="curve")
    for x, y in points:
        draw.ellipse(box((x - 6, y - 6, x + 6, y + 6)), fill="#f5faff")
target = Path(__file__).resolve().parents[1] / "custom_components/cloudflare_ipv6_ddns/brand"
image.resize((256, 256), Image.Resampling.LANCZOS).save(target / "icon.png")
