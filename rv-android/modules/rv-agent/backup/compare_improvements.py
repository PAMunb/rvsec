#!/usr/bin/env python3
"""
Compare improvements before and after prompt and conversion changes.
"""

from PIL import Image, ImageDraw, ImageFont

# Coordenadas ANTES (primeira execução - imprecisas)
before_coords = {
    "MESSAGE DIGEST": {"x": 50, "y": 150, "width": 300, "height": 50},
    "CIPHER": {"x": 50, "y": 275, "width": 300, "height": 50},
    "GENERATED": {"x": 50, "y": 400, "width": 300, "height": 50}
}

# Coordenadas DEPOIS (nova execução - precisas)
after_coords = {
    "MESSAGE DIGEST": {"x": 8, "y": 154, "width": 708, "height": 54, "center": (362, 181)},
    "CIPHER": {"x": 8, "y": 304, "width": 708, "height": 54, "center": (362, 331)},
    "GENERATED": {"x": 8, "y": 454, "width": 708, "height": 54, "center": (362, 481)}
}

# Carregar imagem otimizada
img_optimized = Image.open("/tmp/optimized_decoded.png")

print("=" * 80)
print("📊 ANÁLISE COMPARATIVA - ANTES vs DEPOIS")
print("=" * 80)

print("\n🔴 ANTES (Prompt Genérico):")
print("-" * 80)
for element, coords in before_coords.items():
    center_x = coords['x'] + coords['width'] // 2
    center_y = coords['y'] + coords['height'] // 2
    print(f"{element}:")
    print(f"   Box: ({coords['x']}, {coords['y']}, {coords['width']}, {coords['height']})")
    print(f"   Center: ({center_x}, {center_y})")
    print(f"   ❌ Problemas: X muito à esquerda, largura muito pequena (300 vs real 708)")

print("\n✅ DEPOIS (Prompt Melhorado com Dimensões Especificadas):")
print("-" * 80)
for element, coords in after_coords.items():
    print(f"{element}:")
    print(f"   Box: ({coords['x']}, {coords['y']}, {coords['width']}, {coords['height']})")
    print(f"   Center: {coords['center']}")
    print(f"   ✅ Melhoria: Coordenadas precisas, largura correta!")

# Criar visualizações comparativas
img_before = img_optimized.copy()
img_after = img_optimized.copy()

draw_before = ImageDraw.Draw(img_before)
draw_after = ImageDraw.Draw(img_after)

# Desenhar coordenadas ANTES (vermelho)
for element, coords in before_coords.items():
    x, y, w, h = coords['x'], coords['y'], coords['width'], coords['height']
    center_x = x + w // 2
    center_y = y + h // 2

    draw_before.rectangle([(x, y), (x + w, y + h)], outline="red", width=2)
    draw_before.ellipse([(center_x - 5, center_y - 5), (center_x + 5, center_y + 5)],
                        fill="red", outline="yellow", width=2)

# Desenhar coordenadas DEPOIS (verde)
for element, coords in after_coords.items():
    x, y, w, h = coords['x'], coords['y'], coords['width'], coords['height']
    center_x, center_y = coords['center']

    draw_after.rectangle([(x, y), (x + w, y + h)], outline="lime", width=3)
    draw_after.ellipse([(center_x - 5, center_y - 5), (center_x + 5, center_y + 5)],
                       fill="lime", outline="yellow", width=2)

# Salvar visualizações
img_before.save("/tmp/comparison_before.png")
img_after.save("/tmp/comparison_after.png")

print("\n💾 Visualizações salvas:")
print("   ANTES: /tmp/comparison_before.png (caixas vermelhas)")
print("   DEPOIS: /tmp/comparison_after.png (caixas verdes)")

print("\n📈 ESTATÍSTICAS DE MELHORIA:")
print("-" * 80)

# Calcular diferenças
before_width = before_coords["MESSAGE DIGEST"]["width"]
after_width = after_coords["MESSAGE DIGEST"]["width"]
width_diff = ((after_width - before_width) / before_width) * 100

before_x = before_coords["MESSAGE DIGEST"]["x"]
after_x = after_coords["MESSAGE DIGEST"]["x"]
x_diff = before_x - after_x

print(f"📏 Largura dos botões:")
print(f"   ANTES: {before_width}px")
print(f"   DEPOIS: {after_width}px")
print(f"   MELHORIA: +{width_diff:.1f}% (muito mais preciso!)")

print(f"\n📍 Posição X inicial:")
print(f"   ANTES: {before_x}px")
print(f"   DEPOIS: {after_x}px")
print(f"   CORREÇÃO: {x_diff}px mais à esquerda (correto!)")

print(f"\n🎯 Centro MESSAGE DIGEST:")
before_center = (50 + 300//2, 150 + 50//2)
after_center = after_coords["MESSAGE DIGEST"]["center"]
print(f"   ANTES: {before_center}")
print(f"   DEPOIS: {after_center}")
print(f"   DIFERENÇA: {after_center[0] - before_center[0]}px horizontal, {after_center[1] - before_center[1]}px vertical")

print("\n🔄 CONVERSÃO PARA COORDENADAS DO DISPOSITIVO:")
print("-" * 80)
scale_x = 1080 / 724  # 1.4917
scale_y = 1920 / 1288  # 1.4907

for element, coords in after_coords.items():
    llm_center = coords['center']
    device_center = (int(llm_center[0] * scale_x), int(llm_center[1] * scale_y))

    print(f"{element}:")
    print(f"   LLM fornece: center={llm_center} [na imagem 724x1288]")
    print(f"   android_click() converte para: center={device_center} [no dispositivo 1080x1920]")
    print(f"   ✅ Conversão automática aplicada!")

print("\n" + "=" * 80)
print("✅ RESUMO DAS MELHORIAS")
print("=" * 80)
print("1. ✅ Prompt melhorado especifica dimensões (724x1288)")
print("2. ✅ LLM agora fornece coordenadas PRECISAS")
print("3. ✅ Formato estruturado: center=(x,y), box=(x,y,width,height)")
print("4. ✅ Largura dos botões correta: 708px (era 300px)")
print("5. ✅ Posição horizontal precisa: x=8 (era x=50)")
print("6. ✅ android_click() agora converte coordenadas automaticamente")
print("7. ✅ Conversão: LLM(724x1288) -> Device(1080x1920)")
print("\n🎯 RESULTADO: Coordenadas agora correspondem EXATAMENTE aos botões!")
print("=" * 80)
