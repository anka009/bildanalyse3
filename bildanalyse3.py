import streamlit as st
from PIL import Image, ImageDraw
import numpy as np
from scipy.ndimage import label, find_objects
from io import BytesIO

# 📄 Seiteneinstellungen
st.set_page_config(page_title="Bildanalyse Komfort-App", layout="wide")
st.title("🧪 Bildanalyse Komfort-App")

# 📁 Bild-Upload
uploaded_file = st.sidebar.file_uploader("📁 Bild auswählen", type=["png", "jpg", "jpeg", "tif", "tiff"])
if not uploaded_file:
    st.warning("Bitte zuerst ein Bild hochladen.")
    st.stop()

img_rgb = Image.open(uploaded_file).convert("RGB")
img_gray = img_rgb.convert("L")
img_array = np.array(img_gray)
w, h = img_rgb.size

# 🧠 Beste Schwelle anhand der Fleckengruppenanzahl
def gruppen_histogramm(cropped_array, min_area, max_area, group_diameter):
    schwellen = list(range(30, 200, 5))
    gruppenzahlen = []

    for thresh in schwellen:
        mask = cropped_array < thresh
        labeled_array, _ = label(mask)
        objects = find_objects(labeled_array)
        centers = [((obj[1].start + obj[1].stop) // 2, (obj[0].start + obj[0].stop) // 2)
                   for obj in objects if min_area <= np.sum(labeled_array[obj] > 0) <= max_area]

        grouped, visited = [], set()
        for i, (x1, y1) in enumerate(centers):
            if i in visited: continue
            gruppe = [(x1, y1)]
            visited.add(i)
            for j, (x2, y2) in enumerate(centers):
                if j in visited: continue
                if ((x1 - x2)**2 + (y1 - y2)**2)**0.5 <= group_diameter / 2:
                    gruppe.append((x2, y2))
                    visited.add(j)
            grouped.append(gruppe)

        gruppenzahlen.append(len(grouped))

    return schwellen, gruppenzahlen

def finde_beste_schwelle(cropped_array, min_area, max_area, group_diameter):
    best_score, best_thresh = -1, 0
    for thresh in range(50, 200, 5):
        mask = cropped_array < thresh
        labeled_array, _ = label(mask)
        objects = find_objects(labeled_array)

        centers = [
            ((obj[1].start + obj[1].stop) // 2, (obj[0].start + obj[0].stop) // 2)
            for obj in objects
            if min_area <= np.sum(labeled_array[obj] > 0) <= max_area
        ]

        grouped, visited = [], set()
        for i, (x1, y1) in enumerate(centers):
            if i in visited:
                continue
            gruppe = [(x1, y1)]
            visited.add(i)
            for j, (x2, y2) in enumerate(centers):
                if j in visited:
                    continue
                if ((x1 - x2)**2 + (y1 - y2)**2)**0.5 <= group_diameter / 2:
                    gruppe.append((x2, y2))
                    visited.add(j)
            grouped.append(gruppe)

        score = len(grouped)  # ✅ Bewertet anhand der Gruppenzahl
        if score > best_score:
            best_score, best_thresh = score, thresh

    return best_thresh, best_score

# 🎛️ Sidebar-Einstellungen
modus = st.sidebar.radio("Analyse-Modus wählen", ["Fleckengruppen", "Kreis-Ausschnitt"])
circle_color = st.sidebar.color_picker("🎨 Farbe für Fleckengruppen", "#FF0000")
spot_color = st.sidebar.color_picker("🟦 Farbe für einzelne Flecken", "#00FFFF")
circle_width = st.sidebar.slider("✒️ Liniendicke (Gruppen)", 1, 10, 6)
spot_radius = st.sidebar.slider("🔘 Flecken-Radius", 1, 20, 10)

# ▓▓▓ MODUS: Fleckengruppen ▓▓▓
if modus == "Fleckengruppen":
    st.subheader("🧠 Fleckengruppen erkennen")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 🔧 Einstellungen")
        x_start = st.slider("Start-X", 0, w - 1, 0)
        x_end = st.slider("End-X", x_start + 1, w, w)
        y_start = st.slider("Start-Y", 0, h - 1, 0)
        y_end = st.slider("End-Y", y_start + 1, h, h)
        min_area = st.slider("Minimale Fleckengröße", 10, 500, 30)
        max_area = st.slider("Maximale Fleckengröße", min_area, 1000, 250)
        group_diameter = st.slider("Gruppendurchmesser", 20, 500, 60)

        if "intensity" not in st.session_state:
            st.session_state.intensity = 25
        intensity = st.slider("Intensitäts-Schwelle", 0, 255, st.session_state.intensity)

        if st.button("🔎 Beste Schwelle (Gruppenanzahl) ermitteln"):
            cropped_array = img_array[y_start:y_end, x_start:x_end]
            best_intensity, score = finde_beste_schwelle(cropped_array, min_area, max_area, group_diameter)
            st.session_state.intensity = best_intensity
            st.success(f"✅ Beste Schwelle: {best_intensity} ({score} Gruppen)")

    with col2:
        cropped_array = img_array[y_start:y_end, x_start:x_end]
        mask = cropped_array < intensity
        labeled_array, _ = label(mask)
        objects = find_objects(labeled_array)

        centers = [
            ((obj[1].start + obj[1].stop) // 2, (obj[0].start + obj[0].stop) // 2)
            for obj in objects
            if min_area <= np.sum(labeled_array[obj] > 0) <= max_area
        ]

        if st.button("🟦 Einzelne Flecken anzeigen"):
            draw_img_flecken = img_rgb.copy()
            draw = ImageDraw.Draw(draw_img_flecken)
            if centers:
                for x, y in centers:
                    draw.ellipse(
                        [(x + x_start - spot_radius, y + y_start - spot_radius),
                         (x + x_start + spot_radius, y + y_start + spot_radius)],
                        fill=spot_color
                    )
                st.image(draw_img_flecken, caption="🎯 Einzelne Flecken", use_column_width=True)
            else:
                st.warning("⚠️ Keine Flecken erkannt.")
                st.image(draw_img_flecken, caption="📷 Originalbild", use_column_width=True)

        grouped, visited = [], set()
        for i, (x1, y1) in enumerate(centers):
            if i in visited:
                continue
            gruppe = [(x1, y1)]
            visited.add(i)
            for j, (x2, y2) in enumerate(centers):
                if j in visited:
                    continue
                if ((x1 - x2)**2 + (y1 - y2)**2)**0.5 <= group_diameter / 2:
                    gruppe.append((x2, y2))
                    visited.add(j)
            grouped.append(gruppe)

        st.success(f"📍 Fleckengruppen erkannt: {len(grouped)}")

# 📊 Gruppenzahl-Histogramm anzeigen
def gruppen_histogramm(cropped_array, min_area, max_area, group_diameter):
    schwellen = list(range(30, 200, 5))
    gruppenzahlen = []

    for thresh in schwellen:
        mask = cropped_array < thresh
        labeled_array, _ = label(mask)
        objects = find_objects(labeled_array)
        centers = [((obj[1].start + obj[1].stop) // 2, (obj[0].start + obj[0].stop) // 2)
                   for obj in objects if min_area <= np.sum(labeled_array[obj] > 0) <= max_area]

        grouped, visited = [], set()
        for i, (x1, y1) in enumerate(centers):
            if i in visited: continue
            gruppe = [(x1, y1)]
            visited.add(i)
            for j, (x2, y2) in enumerate(centers):
                if j in visited: continue
                if ((x1 - x2)**2 + (y1 - y2)**2)**0.5 <= group_diameter / 2:
                    gruppe.append((x2, y2))
                    visited.add(j)
            grouped.append(gruppe)

        gruppenzahlen.append(len(grouped))

    return schwellen, gruppenzahlen

# Histogramm berechnen und anzeigen
import matplotlib.pyplot as plt

schwellen, gruppenzahlen = gruppen_histogramm(cropped_array, min_area, max_area, group_diameter)
best_thresh, _ = finde_beste_schwelle(cropped_array, min_area, max_area, group_diameter)

fig, ax = plt.subplots()
ax.bar(schwellen, gruppenzahlen, width=4, color='skyblue', edgecolor='black')
ax.axvline(best_thresh, color='red', linestyle='--', label=f'Beste Schwelle: {best_thresh}')
ax.set_xlabel("Intensitäts-Schwelle")
ax.set_ylabel("Gruppenzahl")
ax.set_title("📊 Gruppenzahl vs. Intensität")
ax.legend()
st.pyplot(fig)

# ▓▓▓ MODUS 2: Kreis-Ausschnitt ▓▓▓

elif modus == "Kreis-Ausschnitt":
    st.subheader("🎯 Kreis-Ausschnitt wählen")
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### 🔧 Kreis-Einstellungen")
        center_x = st.slider("🞄 Mittelpunkt-X", 0, w - 1, w // 2)
        center_y = st.slider("🞄 Mittelpunkt-Y", 0, h - 1, h // 2)
        radius = st.slider("🔵 Radius", 10, min(w, h) // 2, 100)

    with col2:
        draw_img = img_rgb.copy()
        draw = ImageDraw.Draw(draw_img)
        draw.ellipse(
            [(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)],
            outline=circle_color,
            width=circle_width
        )
        st.image(draw_img, caption="🖼️ Kreis-Vorschau", use_column_width=True)

        if st.checkbox("🎬 Nur Ausschnitt anzeigen"):
            mask = Image.new("L", (w, h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse(
                [(center_x - radius, center_y - radius), (center_x + radius, center_y + radius)],
                fill=255
            )
            cropped = Image.composite(img_rgb, Image.new("RGB", img_rgb.size, (255, 255, 255)), mask)
            st.image(cropped, caption="🧩 Kreis-Ausschnitt", use_column_width=True)

            buf = BytesIO()
            cropped.save(buf, format="PNG")
            byte_im = buf.getvalue()
            st.download_button(
                label="📥 Kreis-Ausschnitt herunterladen",
                data=byte_im,
                file_name="kreis_ausschnitt.png",
                mime="image/png"
            )
