import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.drawing.image import Image

DB_NAME = "feedback_analytics.db"
OUTPUT_FILE = "customer_feedback_insights.xlsx"

def generate_excel_dashboard():
    """
    Queries SQL tables, analyzes the results, and structures a highly styled
    corporate Excel report featuring KPI blocks, formatted tables, and embedded charts.
    """
    print("[Excel Generator] Fetching analytical data for the dashboard...")
    
    # 1. Fetch data from SQLite
    conn = sqlite3.connect(DB_NAME)
    df_raw = pd.read_sql_query("SELECT * FROM customer_feedback", conn)
    
    # Query aggregated stats
    df_category = pd.read_sql_query("""
        SELECT 
            feedback_category as "Category",
            COUNT(*) as "Total Feedbacks",
            ROUND(AVG(rating), 2) as "Average Rating",
            ROUND(AVG(sentiment_score), 2) as "Average Sentiment Score"
        FROM customer_feedback
        GROUP BY feedback_category
        ORDER BY COUNT(*) DESC
    """, conn)
    conn.close()

    # 2. Generate Matplotlib visualization to embed in Excel
    print("[Excel Generator] Rendering visualization chart...")
    plt.figure(figsize=(10, 5))
    
    # Dual chart: Left = Category counts, Right = Sentiment Distribution
    plt.subplot(1, 2, 1)
    category_counts = df_raw["feedback_category"].value_counts()
    sns.barplot(x=category_counts.values, y=category_counts.index,
                hue=category_counts.index, palette="Blues_d", legend=False)
    plt.title("Feedback Count by Category", fontsize=11, fontweight='bold', pad=10)
    plt.xlabel("Count")
    
    plt.subplot(1, 2, 2)
    sentiment_counts = df_raw["sentiment_class"].value_counts()
    colors = ["#4CAF50", "#F44336", "#FFC107"] # Green, Red, Yellow
    plt.pie(sentiment_counts, labels=sentiment_counts.index, autopct='%1.1f%%', 
            colors=[colors[i % 3] for i in range(len(sentiment_counts))], startangle=140,
            textprops={'fontsize': 10})
    plt.title("Sentiment Distribution", fontsize=11, fontweight='bold', pad=10)
    
    plt.tight_layout()
    chart_path = "temp_sentiment_chart.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()

    # 3. Build workbook using openpyxl
    print("[Excel Generator] Formatting Excel Workbook...")
    wb = Workbook()
    
    # Setup sheets
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    ws_raw = wb.create_sheet(title="Raw Feedback Data")
    
    # Turn grid lines ON (standard professional practice)
    ws_summary.views.sheetView[0].showGridLines = True
    ws_raw.views.sheetView[0].showGridLines = True
    
    # Styling assets
    navy_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    light_blue_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
    white_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)
    header_font = Font(name="Calibri", size=16, bold=True, color="1F4E78")
    
    thin_border = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='BFBFBF'),
        bottom=Side(style='thin', color='BFBFBF')
    )
    
    # ==================== SUMMARY SHEET BUILD ====================
    # Title Block
    ws_summary["A1"] = "CUSTOMER FEEDBACK INSIGHTS DASHBOARD"
    ws_summary["A1"].font = header_font
    ws_summary.row_dimensions[1].height = 30
    
    ws_summary["A2"] = "AI-Analyzed Feedbacks & Sentiment Reports (Live SQLite Data Source)"
    ws_summary["A2"].font = Font(name="Calibri", size=11, italic=True, color="595959")
    
    # KPI Blocks
    # KPI 1: Total Volume
    ws_summary.merge_cells("A4:B4")
    ws_summary["A4"] = "TOTAL FEEDBACKS"
    ws_summary["A4"].fill = navy_fill
    ws_summary["A4"].font = white_font
    ws_summary["A4"].alignment = Alignment(horizontal="center")
    
    ws_summary.merge_cells("A5:B5")
    ws_summary["A5"] = f"=COUNTA('Raw Feedback Data'!A2:A{len(df_raw)+1})"
    ws_summary["A5"].font = Font(name="Calibri", size=18, bold=True)
    ws_summary["A5"].alignment = Alignment(horizontal="center")
    ws_summary["A5"].border = thin_border
    
    # KPI 2: Average Rating
    ws_summary.merge_cells("D4:E4")
    ws_summary["D4"] = "AVERAGE RATING"
    ws_summary["D4"].fill = navy_fill
    ws_summary["D4"].font = white_font
    ws_summary["D4"].alignment = Alignment(horizontal="center")
    
    ws_summary.merge_cells("D5:E5")
    ws_summary["D5"] = f"=AVERAGE('Raw Feedback Data'!D2:D{len(df_raw)+1})"
    ws_summary["D5"].font = Font(name="Calibri", size=18, bold=True)
    ws_summary["D5"].alignment = Alignment(horizontal="center")
    ws_summary["D5"].number_format = '0.00'
    ws_summary["D5"].border = thin_border
    
    # KPI 3: Avg Sentiment
    ws_summary.merge_cells("G4:H4")
    ws_summary["G4"] = "NET SENTIMENT SCORE"
    ws_summary["G4"].fill = navy_fill
    ws_summary["G4"].font = white_font
    ws_summary["G4"].alignment = Alignment(horizontal="center")
    
    ws_summary.merge_cells("G5:H5")
    ws_summary["G5"] = f"=AVERAGE('Raw Feedback Data'!H2:H{len(df_raw)+1})"
    ws_summary["G5"].font = Font(name="Calibri", size=18, bold=True)
    ws_summary["G5"].alignment = Alignment(horizontal="center")
    ws_summary["G5"].number_format = '0.00'
    ws_summary["G5"].border = thin_border
    
    # Category Breakdowns Table
    ws_summary["A7"] = "FEEDBACK BREAKDOWN BY CATEGORY"
    ws_summary["A7"].font = Font(name="Calibri", size=12, bold=True, color="1F4E78")
    
    headers = list(df_category.columns)
    for col_num, header in enumerate(headers, 1):
        cell = ws_summary.cell(row=8, column=col_num)
        cell.value = header
        cell.fill = navy_fill
        cell.font = white_font
        cell.alignment = Alignment(horizontal="center")
        cell.border = thin_border
        
    for row_idx, row_data in enumerate(dataframe_to_rows(df_category, index=False, header=False), 9):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws_summary.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.font = regular_font
            cell.border = thin_border
            if col_idx in [3, 4]:
                cell.number_format = '0.00'
                cell.alignment = Alignment(horizontal="right")
            else:
                cell.alignment = Alignment(horizontal="left" if col_idx == 1 else "center")
                
    # Embed the Matplotlib Chart
    if os.path.exists(chart_path):
        img = Image(chart_path)
        img.width = 550
        img.height = 275
        # Place chart on row 16
        ws_summary.add_image(img, "A16")
        
    # ==================== RAW DATA SHEET BUILD ====================
    # Print headers for raw data
    raw_headers = list(df_raw.columns)
    for col_num, header in enumerate(raw_headers, 1):
        cell = ws_raw.cell(row=1, column=col_num)
        cell.value = header.replace("_", " ").upper()
        cell.fill = navy_fill
        cell.font = white_font
        cell.alignment = Alignment(horizontal="center")
        
    # Print data rows
    for row_idx, row_data in enumerate(dataframe_to_rows(df_raw, index=False, header=False), 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws_raw.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.font = regular_font
            cell.border = thin_border
            
            # Format alignment and formats
            if col_idx in [4, 8]:  # Rating or Sentiment Score
                cell.number_format = '0.0' if col_idx == 8 else '0'
                cell.alignment = Alignment(horizontal="right")
            elif col_idx in [1, 6]:  # ID or Date
                cell.alignment = Alignment(horizontal="center")
            else:
                cell.alignment = Alignment(horizontal="left")

    # Set column widths dynamically for both sheets
    for ws in [ws_summary, ws_raw]:
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                if cell.value:
                    val_str = str(cell.value)
                    if not val_str.startswith('='): # skip formulas for width check
                        max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
            
    # Set explicit widths for key summary columns
    ws_summary.column_dimensions['A'].width = 22
    ws_summary.column_dimensions['B'].width = 18
    ws_summary.column_dimensions['C'].width = 18
    ws_summary.column_dimensions['D'].width = 25

    # Save Excel workbook
    wb.save(OUTPUT_FILE)
    print(f"[Excel Generator] Excel dashboard saved as '{OUTPUT_FILE}'.")
    
    # Cleanup temp chart file
    if os.path.exists(chart_path):
        os.remove(chart_path)
        print("[Excel Generator] Temporary chart image cleaned up.")

if __name__ == "__main__":
    generate_excel_dashboard()
