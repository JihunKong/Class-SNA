#!/usr/bin/env python3
"""
개인정보 수집·이용 동의서 PDF 생성 스크립트
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
import os

# 한글 폰트 등록
def register_korean_font():
    """한글 폰트 등록"""
    # 프로젝트 내 폰트 파일 경로 (우선)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_font = os.path.join(script_dir, '..', 'app', 'static', 'fonts', 'NanumGothic.ttf')

    font_paths = [
        os.path.abspath(project_font),  # 프로젝트 내 폰트
        '/usr/share/fonts/truetype/nanum/NanumGothic.ttf',  # Linux (Docker)
        '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf',  # Linux 대안
        'C:/Windows/Fonts/malgun.ttf',  # Windows
    ]

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Korean', font_path))
                print(f"폰트 로드 성공: {font_path}")
                return 'Korean'
            except Exception as e:
                print(f"폰트 로드 실패 ({font_path}): {e}")
                continue

    # 폰트를 찾지 못한 경우 기본 폰트 사용
    print("경고: 한글 폰트를 찾지 못했습니다. Helvetica로 대체합니다.")
    return 'Helvetica'

def create_consent_pdf(output_path):
    """동의서 PDF 생성"""

    font_name = register_korean_font()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()

    # 스타일 정의
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=18,
        spaceAfter=6*mm,
        alignment=1  # Center
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=12,
        spaceAfter=10*mm,
        alignment=1,
        textColor=colors.grey
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=12,
        spaceBefore=8*mm,
        spaceAfter=3*mm,
        textColor=colors.HexColor('#333333')
    )

    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=14,
        spaceAfter=2*mm
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=10*mm,
        bulletIndent=5*mm
    )

    signature_style = ParagraphStyle(
        'Signature',
        parent=body_style,
        alignment=1,
        spaceBefore=5*mm
    )

    story = []

    # 제목
    story.append(Paragraph("개인정보 수집·이용 동의서", title_style))
    story.append(Paragraph("(학급 관계 네트워크 분석 활동용)", subtitle_style))

    # 1. 수집 목적
    story.append(Paragraph("1. 수집 목적", heading_style))
    story.append(Paragraph(
        "학급 내 학생 간의 관계(친구, 학습 도움, 함께하고 싶은 친구 등)를 분석하여 "
        "학급 운영 및 교육 활동에 활용합니다.",
        body_style
    ))

    # 2. 수집 항목
    story.append(Paragraph("2. 수집 항목", heading_style))
    story.append(Paragraph("• 학생 이름 또는 식별자 (학번, 별명 등 비식별 정보 권장)", bullet_style))
    story.append(Paragraph("• 설문 응답 내용 (친구 관계, 학습 도움 관계 등)", bullet_style))

    # 3. 보유 기간
    story.append(Paragraph("3. 보유 기간", heading_style))
    story.append(Paragraph(
        "해당 학기 종료 시까지 (분석 완료 후 담당 교사가 직접 삭제)",
        body_style
    ))

    # 4. 열람 권한
    story.append(Paragraph("4. 열람 권한", heading_style))
    story.append(Paragraph("• 담당 교사만 열람 가능", bullet_style))
    story.append(Paragraph("• 개발자, 외부인 등 제3자는 열람 불가", bullet_style))
    story.append(Paragraph("• 분석 결과는 담당 교사에게만 제공됨", bullet_style))

    # 5. 동의 거부 권리
    story.append(Paragraph("5. 동의 거부 권리", heading_style))
    story.append(Paragraph(
        "귀하는 개인정보 수집·이용에 대한 동의를 거부할 권리가 있으며, "
        "동의를 거부할 경우 해당 활동에 참여하지 않을 수 있습니다.",
        body_style
    ))

    # 6. 안내 사항
    story.append(Paragraph("6. 안내 사항", heading_style))
    story.append(Paragraph("• 수집된 정보는 교육 목적 외에는 사용되지 않습니다.", bullet_style))
    story.append(Paragraph("• 실명 대신 가명, 학번, 별명 등 비식별 정보를 사용할 수 있습니다.", bullet_style))
    story.append(Paragraph("• 분석 결과는 학급 전체의 관계 패턴 이해에 활용됩니다.", bullet_style))
    story.append(Paragraph("• 개인별 결과는 공개되지 않으며, 전체 네트워크 분석에만 사용됩니다.", bullet_style))

    # 서비스 정보
    story.append(Paragraph("7. 서비스 정보", heading_style))
    story.append(Paragraph("• 서비스명: Class-SNA (학급 관계 네트워크 분석 시스템)", bullet_style))
    story.append(Paragraph("• 웹사이트: https://class-sna.com", bullet_style))
    story.append(Paragraph("• 개인정보 보호책임자: 공지훈 (purusil55@gmail.com)", bullet_style))

    story.append(Spacer(1, 15*mm))

    # 동의 문구
    story.append(Paragraph(
        "본인은 위의 내용을 충분히 이해하였으며, 개인정보 수집·이용에 동의합니다.",
        signature_style
    ))

    story.append(Spacer(1, 10*mm))

    # 서명란 테이블
    signature_data = [
        ['날 짜', '년        월        일'],
        ['학생 성명', '                              (서명)'],
        ['학부모 성명', '                              (서명)'],
    ]

    signature_table = Table(signature_data, colWidths=[40*mm, 100*mm])
    signature_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8*mm),
        ('TOPPADDING', (0, 0), (-1, -1), 3*mm),
        ('LINEBELOW', (1, 0), (1, -1), 0.5, colors.black),
    ]))

    story.append(signature_table)

    # 하단 안내
    story.append(Spacer(1, 15*mm))

    footer_style = ParagraphStyle(
        'Footer',
        parent=body_style,
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )

    story.append(Paragraph(
        "※ 본 동의서는 학교에서 보관하며, 동의 철회 시 담당 교사에게 요청하시기 바랍니다.",
        footer_style
    ))
    story.append(Paragraph(
        "※ 개인정보 관련 문의: purusil55@gmail.com",
        footer_style
    ))

    # PDF 생성
    doc.build(story)
    print(f"동의서 PDF 생성 완료: {output_path}")


if __name__ == "__main__":
    output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = os.path.join(output_dir, "app", "static", "docs", "consent_form.pdf")

    # 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    create_consent_pdf(output_path)
