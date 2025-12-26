from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import os
import sys
from io import BytesIO
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import re

load_dotenv()

app = Flask(__name__)
CORS(app)

API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env file!", file=sys.stderr)
else:
    print(f"API Key loaded: {API_KEY[:10]}..." if len(API_KEY) > 10 else "API Key loaded")
    
genai.configure(api_key=API_KEY)

try:
    models = genai.list_models()
    print("Available models:")
    for model in models:
        if 'generateContent' in model.supported_generation_methods:
            print(f"  - {model.name}")
except Exception as e:
    print(f"Could not list models: {e}", file=sys.stderr)

def generate_travel_plan(source, destination, dates, travelers, interests):
    prompt = f"""You are an expert travel planner. Create a detailed travel itinerary based on the following information:

Source: {source}
Destination: {destination}
Travel Dates: {dates}
Number of Travelers: {travelers}
Interests: {interests}

Please provide a comprehensive travel plan that includes:
1. Day-by-day itinerary
2. Recommended accommodations
3. Transportation options
4. Must-visit attractions based on their interests
5. Local restaurants and food recommendations
6. Budget estimates
7. Tips and important information

Format the response in a clear, organized manner with sections and bullet points where appropriate."""

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)
    
    return response.text

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/generate-itinerary', methods=['POST'])
def generate_itinerary():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid or missing JSON body'}), 400
        
        source = data.get('source')
        destination = data.get('destination')
        dates = data.get('dates')
        travelers = data.get('travelers')
        interests = data.get('interests')
        
        if not all([source, destination, dates, travelers, interests]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        itinerary = generate_travel_plan(source, destination, dates, travelers, interests)
        
        return jsonify({
            'success': True,
            'itinerary': itinerary
        }), 200
        
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR generating itinerary: {error_msg}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

def parse_itinerary_sections(itinerary_text):
    lines = itinerary_text.split('\n')
    sections = []
    current_section = None
    current_content = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_content:
                current_content.append('') 
            continue
            
        if line and (line.startswith('##') or line.startswith('**') or line.isupper() or 
                     re.match(r'^(Day\s+\d+|Accommodation|Transportation|Attraction|Restaurant|Budget|Tip)', line, re.IGNORECASE)):
            if current_section is not None:
                sections.append({'title': current_section, 'content': '\n'.join(current_content)})
            elif current_content:
                sections.append({'title': 'Trip Overview', 'content': '\n'.join(current_content)})
            current_section = line.replace('##', '').replace('**', '').strip().replace('*', '')
            current_content = []
        else:
            line = line.lstrip('*- ').strip()
            if line:
                current_content.append(line)
    
    if current_section is not None:
        sections.append({'title': current_section, 'content': '\n'.join(current_content)})
    elif current_content:
        sections.append({'title': 'Trip Overview', 'content': '\n'.join(current_content)})
    
    return sections

@app.route('/api/export-pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid or missing JSON body'}), 400
        
        source = data.get('source', '')
        destination = data.get('destination', '')
        dates = data.get('dates', '')
        travelers = data.get('travelers', '')
        interests = data.get('interests', '')
        itinerary = data.get('itinerary', '')
        
        if not itinerary:
            return jsonify({'error': 'No itinerary to export'}), 400
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter,
                              rightMargin=0.6*inch, leftMargin=0.6*inch,
                              topMargin=0.75*inch, bottomMargin=0.75*inch)
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=6,
            alignment=1,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#764ba2'),
            spaceAfter=20,
            alignment=1,
            fontName='Helvetica-Oblique'
        )
        
        trip_info_style = ParagraphStyle(
            'TripInfo',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=4,
            leading=16,
            fontName='Helvetica'
        )
        
        section_heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Normal'],
            fontSize=13,
            textColor=colors.black,
            spaceAfter=6,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        )
        
        subsection_style = ParagraphStyle(
            'SubSection',
            parent=styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#764ba2'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['BodyText'],
            fontSize=10,
            spaceAfter=6,
            leading=14,
            fontName='Helvetica'
        )
        
        bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14,
            leftIndent=20,
            fontName='Helvetica'
        )
        
        elements = []
        
        elements.append(Paragraph("Muzammils Travel Plan AI", title_style))
        elements.append(Paragraph(f"Discover {destination}", subtitle_style))
        elements.append(Spacer(1, 0.15*inch))
        
        trip_info_table = [
            [Paragraph("<b>Destination:</b>", trip_info_style), Paragraph(destination, trip_info_style)],
            [Paragraph("<b>From:</b>", trip_info_style), Paragraph(source, trip_info_style)],
            [Paragraph("<b>Dates:</b>", trip_info_style), Paragraph(dates, trip_info_style)],
            [Paragraph("<b>Travelers:</b>", trip_info_style), Paragraph(str(travelers), trip_info_style)],
            [Paragraph("<b>Interests:</b>", trip_info_style), Paragraph(interests, trip_info_style)]
        ]
        
        info_table = Table(trip_info_table, colWidths=[1.5*inch, 4.5*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        sections = parse_itinerary_sections(itinerary)
        
        for idx, section in enumerate(sections):
            if idx > 0 and idx % 3 == 0:
                elements.append(PageBreak())
            
            title = section['title'].strip()
            content = section['content'].strip()
            
            elements.append(Paragraph(title, section_heading_style))
            
            if content:
                content_lines = content.split('\n')
                for line in content_lines:
                    line = line.strip()
                    if not line:
                        elements.append(Spacer(1, 0.1*inch))
                    elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                        clean_line = line.lstrip('-•* ').strip()
                        elements.append(Paragraph(f"• {clean_line}", bullet_style))
                    elif ':' in line and len(line) < 100:
                        elements.append(Paragraph(line, subsection_style))
                    else:
                        elements.append(Paragraph(line, body_style))
            
            elements.append(Spacer(1, 0.08*inch))
        
        elements.append(Spacer(1, 0.3*inch))
        footer_text = f"<i>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i>"
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor=colors.grey, alignment=1)
        elements.append(Paragraph(footer_text, footer_style))
        
        doc.build(elements)
        buffer.seek(0)
        
        filename = f"travel_plan_{destination}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR exporting PDF: {error_msg}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': error_msg
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
