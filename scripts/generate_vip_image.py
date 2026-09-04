# scripts/generate_vip_image.py - Auto-generates VIP 4-leg ACCA graphic
from PIL import Image, ImageDraw
import os

def generate():
    os.makedirs("public", exist_ok=True)
    W, H = 1600, 900
    img = Image.new("RGB", (W, H), "#050507")
    draw = ImageDraw.Draw(img, "RGBA")

    # Stadium bokeh lights (aesthetic)
    lights = [(200,180,70, 35), (1400,220,60, 30), (300,700,50, 25), (1300,700,55, 28), (100,500,40, 20), (1500,500,45, 22)]
    for x,y,r,a in lights:
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(255,240,180, a))

    # Main glass card
    cx, cy, cw, ch = 400, 80, 800, 740
    draw.rounded_rectangle([cx, cy, cx+cw, cy+ch], radius=32, fill=(255,255,255,18), outline=(34,197,94,90), width=2)
    draw.rounded_rectangle([cx+2, cy+2, cx+cw-2, cy+ch-2], radius=30, outline=(255,255,255,30), width=1)

    # Crown dot
    draw.ellipse([W//2-22, cy+35, W//2+22, cy+65], outline=(34,197,94,200), width=2)
    draw.text((W//2-12, cy+32), "V", fill=(34,197,94,255))

    # 4 legs - glass rows
    for i in range(4):
        y = cy + 110 + i*155
        # row
        draw.rounded_rectangle([cx+30, y, cx+cw-30, y+110], radius=20, fill=(255,255,255,12), outline=(255,255,255,35), width=1)
        # icon circle
        draw.ellipse([cx+60, y+25, cx+120, y+85], outline=(34,197,94,150), width=2)
        # green progress bar (like your screenshot)
        draw.rounded_rectangle([cx+160, y+40, cx+cw-60, y+70], radius=15, fill=(255,255,255,20), outline=(255,255,255,40), width=1)
        draw.rounded_rectangle([cx+170, y+47, cx+cw-70, y+63], radius=8, fill=(74,222,128,255))

    img.save("public/vip-acca.jpg", "JPEG", quality=95)
    
    # Mobile 9:16 version
    mobile = img.crop((W//2-450, 0, W//2+450, H))
    mobile = mobile.resize((1080, 1920))
    mobile.save("public/vip-acca-mobile.jpg", "JPEG", quality=95)
    print("✅ Generated public/vip-acca.jpg + vip-acca-mobile.jpg")

if __name__ == "__main__":
    generate()
