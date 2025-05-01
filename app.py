from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import io
import datetime
from collections import defaultdict

# 폰트 등록
pdfmetrics.registerFont(TTFont('NanumGothic', 'NanumGothic.ttf'))
pdfmetrics.registerFont(TTFont('NanumGothic-Bold', 'NanumGothicBold.ttf'))

app = Flask(__name__)
CORS(app)  # CORS 허용

# 이상치별 심각도 사전 정의
severity_mapping = {
    "pH 이상": "경미",
    "온도 급등": "주의",
    "전압 불안정": "심각",
    "습도 저하": "주의",
    "압력 이상": "심각",
    "온도 급락": "심각",
}

@app.route('/')
def home():
    return "Hello Flask Server!"

@app.route('/generate-summary', methods=['POST'])
def generate_summary():
    data = request.get_json()
    logs = data.get('logs', [])

    if not logs:
        return jsonify({'summary': '⚠️ 이상 로그 없음', 'detailed': []})

    detailed_logs = []
    for log in logs:
        time = log.get('time', '')
        type_part = log.get('type', '')
        value_part = log.get('value', '')
        try:
            value_number = float(value_part)
        except ValueError:
            continue

        if "pH" in type_part:
            if value_number <= 5.5 or value_number > 8.2:
                severity = "심각"
            elif 5.5 < value_number <= 6 or 7.9 <= value_number <= 8.2:
                severity = "주의"
            else:
                severity = "경미"

        elif "온도" in type_part:
            if value_number <= 38.2 or value_number > 43.7:
                severity = "심각"
            elif 38.2 < value_number <= 38.3 or 43.3 <= value_number <= 43.7:
                severity = "주의"
            else:
                severity = "경미"

        elif "전압" in type_part:
            if value_number <= 14.1 or value_number > 17.5:
                severity = "심각"
            elif 14.1 <= value_number < 14.3 or 17.2 <= value_number <= 17.5:
                severity = "주의"
            else:
                severity = "경미"

        detailed_logs.append({
            'time': time,
            'type': type_part,
            'value': value_part,
            'severity': severity
        })

    return jsonify({
        'summary': f'총 {len(detailed_logs)}건의 이상이 탐지되었습니다.',
        'detailed': detailed_logs
    })

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    data = request.get_json()
    logs = data.get('logs', [])

    summary_counts = defaultdict(lambda: defaultdict(int))

    for log in logs:
        type_ = log.get("type", "")
        severity = log.get("severity", "")
    
        if "pH" in type_:
            summary_counts["pH 이상"][severity] += 1
        elif "온도" in type_:
            summary_counts["온도 이상"][severity] += 1
        elif "전압" in type_:
            summary_counts["전압 이상"][severity] += 1
            
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    start_x = (width - 400) / 2  # 전체 너비 약 400 기준 중앙 정렬
    col_time = start_x + 65
    col_type = start_x + 180
    col_value = start_x + 270
    col_severity = start_x + 360

    # 📌 제목 박스 스타일
    p.setFillColorRGB(0.93, 0.95, 1)
    p.roundRect(40, y - 15, width - 80, 40, radius=6, fill=True, stroke=False)
    p.setFont("NanumGothic-Bold", 18)
    p.setFillColor(colors.darkblue)
    p.drawCentredString(width / 2, y - 2, "📋 이상 로그 리포트")
    y -= 60

    # 리포트 제목 아래
    p.setFont("NanumGothic-Bold", 11)
    p.setFillColor(colors.black)
    p.drawCentredString(width / 2, y + 20, f"총 {len(logs)}건의 이상 로그가 탐지되었습니다.")
    y -= 18

    # 이상 항목별 상세 요약
    p.setFont("NanumGothic", 10)
    for anomaly_type in ["pH 이상", "온도 이상", "전압 이상"]:
        counts = summary_counts[anomaly_type]
        text = (
            f"- {anomaly_type}: "
            f"심각 {counts.get('심각', 0)}건, "
            f"주의 {counts.get('주의', 0)}건, "
            f"경미 {counts.get('경미', 0)}건"
        )
        p.drawCentredString(width / 2, y + 15, text)
        y -= 16

    # 📌 컬럼 헤더
    p.setFont("NanumGothic-Bold", 12)
    p.setFillColorRGB(0.13, 0.29, 0.58)
    p.setFillColor(colors.white)
    p.setStrokeColor(colors.lightgrey)
    p.setFillColorRGB(0.13, 0.29, 0.58)
    p.rect(40, y - 5, width - 80, 22, fill=True, stroke=False)
    p.setFillColor(colors.white)
    p.drawCentredString(col_time, y + 1, "시간")
    p.drawCentredString(col_type, y + 1, "이상 항목")
    p.drawCentredString(col_value, y + 1, "값")
    p.drawCentredString(col_severity, y + 1, "심각도")
    y -= 25

    # 📄 본문 로그 반복
    p.setFont("NanumGothic", 10)
    row_color_toggle = True

    for idx, log in enumerate(logs):
        time = log.get("time", "")
        type_ = log.get("type", "")
        value = log.get("value", "")
        severity = log.get("severity", "")

        # ⬜ 줄마다 배경 색 번갈아 적용
        if row_color_toggle:
            p.setFillColorRGB(0.98, 0.98, 0.98)  # 연회색
        else:
            p.setFillColor(colors.whitesmoke)
        p.rect(40, y - 2, width - 80, 18, fill=True, stroke=False)
        row_color_toggle = not row_color_toggle

        # ⚠️ 심각도 색상 텍스트 설정
        if severity == "심각":
            sev_color = colors.red
        elif severity == "주의":
            sev_color = colors.orange
        else:
            sev_color = colors.green

        # 텍스트 출력
        p.setFillColor(colors.black)
        p.drawCentredString(col_time, y + 2, time)
        p.drawCentredString(col_type, y + 2, type_)
        p.drawCentredString(col_value, y + 2, f"({value})")

        p.setFillColor(sev_color)
        p.drawCentredString(col_severity, y + 2, severity)

        y -= 20
        if y < 60:
            p.showPage()
            p.setFont("NanumGothic", 10)
            y = height - 50

    # 📆 하단 푸터
    p.setFont("NanumGothic", 9)
    p.setFillColor(colors.gray)
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    p.drawString(50, 30, f"생성일: {date_str}")
    p.drawRightString(width - 50, 30, f"Page {p.getPageNumber()}")

    p.save()
    buffer.seek(0)

    today = datetime.date.today().strftime("%Y%m%d")
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"report_{today}.pdf",
        mimetype='application/pdf'
    )



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
