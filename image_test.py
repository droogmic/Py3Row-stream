from PIL import Image, ImageDraw, ImageFont

base = Image.open("v1.png").convert('RGBA')

txt = Image.new('RGBA', base.size, (255,255,255,0))

# get a font
distfnt = ImageFont.truetype('Pillow/Tests/fonts/DejaVuSans.ttf', 20)
otherfnt = ImageFont.truetype('Pillow/Tests/fonts/DejaVuSans.ttf', 16)

BOX_X = [30, 150, 1060, 1180]
POS_Y = [635, 655, 680]
print([(x, POS_Y[0]) for x in BOX_X] + [(x, POS_Y[2]) for x in BOX_X])
POSITIONS = {
    # 'dist': [
    #     (30,655),
    #     (150,655),
    #     (1060,655),
    #     (1180,655),
    # ],
    # 'other': [
    #     (1060,675),
    #     (1180,675),
    #     (1060,635),
    #     (1180,635),
    # ]
    'dist': [(x, POS_Y[1]) for x in BOX_X],
    'other': [(x, POS_Y[0]) for x in BOX_X] + [(x, POS_Y[2]) for x in BOX_X],
}

# get a drawing context
d = ImageDraw.Draw(txt)

# draw text, half opacity
# d.text((1270,10), "Hello", font=fnt, fill=(255,255,255,128))
# draw text, full opacity
# d.text((10,60), "World", font=fnt, fill=(255,255,255,255))
for pos in POSITIONS['dist']:
    d.text(pos, "1000m", font=distfnt, fill=(255,255,255,255))
for pos in POSITIONS['other']:
    d.text(pos, "1:58r20", font=otherfnt, fill=(255,255,255,255))

out = Image.alpha_composite(base, txt)

out.show()
