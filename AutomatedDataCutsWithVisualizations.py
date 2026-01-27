import streamlit as st
import pymysql
import pandas as pd
import io
import matplotlib.pyplot as plt
import textwrap

# Set Streamlit page configuration
st.set_page_config(
    page_title="GreenlightIQ",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)

dataset_option = st.sidebar.selectbox(
    "Pick a dataset",
    ["Sports Fandom Study", "Content Fandom Study", "Linear TV Study", "Young People Study", "Drivers of Sports Fandom (new)", "Shark Tank Study", "Female Focused Media Study", "Morning Drive Study"]
)

if dataset_option == "Sports Fandom Study":
    responses_table = "responses_1"
    question_mapping_table = "question_mapping_1"
    FE_responses_table = "FE_responses_1"
    FE_EL_mapping_table = "FE_EL_mapping_1"
elif dataset_option == "Content Fandom Study":
    responses_table = "responses_2"
    question_mapping_table = "question_mapping_2"
    FE_responses_table = "FE_responses_2"
    FE_EL_mapping_table = "FE_EL_mapping_2"
elif dataset_option == "Linear TV Study":
    responses_table = "responses_4"
    question_mapping_table = "question_mapping_4"
    FE_responses_table = "FE_responses_4"
    FE_EL_mapping_table = "FE_EL_mapping_4"
elif dataset_option == "Drivers of Sports Fandom (new)":
    responses_table = "responses_5"
    question_mapping_table = "question_mapping_5"
    FE_responses_table = "FE_responses_5"
    FE_EL_mapping_table = "FE_EL_mapping_5"
elif dataset_option == "Shark Tank Study":
    responses_table = "responses_6"
    question_mapping_table = "question_mapping_6"
    FE_responses_table = "FE_responses_6"
    FE_EL_mapping_table = "FE_EL_mapping_6"
elif dataset_option == "Female Focused Media Study":
    responses_table = "responses_7"
    question_mapping_table = "question_mapping_7"
    FE_responses_table = "FE_responses_7"
    FE_EL_mapping_table = "FE_EL_mapping_7"
elif dataset_option == "Morning Drive Study":
    responses_table = "responses_8"
    question_mapping_table = "question_mapping_8"
    FE_responses_table = "FE_responses_8"
    FE_EL_mapping_table = "FE_EL_mapping_8"
else:  # Test Dataset
    responses_table = "responses_3"
    question_mapping_table = "question_mapping_3"
    FE_responses_table = "FE_responses_3"
    FE_EL_mapping_table = "FE_EL_mapping_3"


# Function to apply user-customized theme
def apply_custom_theme():
    background_color = st.sidebar.color_picker("Choose Background Color", "#f4f4f9")
    text_color = st.sidebar.color_picker("Choose Text Color", "#000000")
    button_color = st.sidebar.color_picker("Choose Button Color", "#ff7f0e")

    st.markdown(f"""
        <style>
            body {{
                background-color: {background_color};
                color: {text_color};
            }}
            .stButton>button {{
                background-color: {button_color};
                color: white;
                font-weight: bold;
            }}
            .css-1b7ki0p {{
                background-color: {background_color};
            }}
        </style>
    """, unsafe_allow_html=True)


# Connect to the MySQL database
def connect_to_db():
    try:
        connection.close()  # Close any existing connection
    except:
        pass  # Ignore error if no connection exists

    connection = pymysql.connect(
        host= 'database-1.c5isyysu810z.us-east-2.rds.amazonaws.com',
        user='admin',
        password='Omega1745!',
        database='study_data',
        port=3306,
    )
    return connection
connection = connect_to_db()

with st.expander("📊 View Full Study (All Questions & Answers)"):
    query = f"""
    SELECT q_question_code, s_question_text, answer_text, question_category
    FROM {question_mapping_table}
    ORDER BY q_question_code, answer_text
    """
    study_df = pd.read_sql(query, connection)
    
    st.dataframe(study_df, use_container_width=True)

# Clear Streamlit cache
st.cache_data.clear()

# Fetch data and sample size
def fetch_data_and_sample_size(connection, selected_questions):

    question_code_filter = "', '".join(selected_questions)
    if question_code_filter:
        # Calculate the sample size: Participants who said "Yes" to all selected questions
        sample_size_query = f"""
        SELECT COUNT(DISTINCT participant_id) AS sample_size
        FROM (
            SELECT participant_id
            FROM {responses_table}
            WHERE LOWER(response_text) = 'yes'
            AND question_code IN ('{question_code_filter}')
            GROUP BY participant_id
            HAVING COUNT(DISTINCT question_code) = {len(selected_questions)}
        ) AS filtered_participants
        """
    else:
        sample_size_query = "SELECT 0 AS sample_size"

    sample_size_df = pd.read_sql(sample_size_query, connection)
    sample_size = sample_size_df['sample_size'][0] if not sample_size_df.empty else 0

    if question_code_filter:
    # Main query for data
        query = f"""
        WITH filtered_responses AS (
            SELECT participant_id
            FROM {responses_table}
            WHERE LOWER(response_text) = 'yes'
            AND question_code IN ('{question_code_filter}')
            GROUP BY participant_id
            HAVING COUNT(DISTINCT question_code) = {len(selected_questions)}
        ),
        cut_percentage AS (
            SELECT 
                question_code,
                ROUND(COUNT(CASE WHEN LOWER(response_text) = 'yes' THEN 1 END) * 100.0 / 
                      COUNT(CASE WHEN LOWER(response_text) IN ('yes', 'no') THEN 1 END)) AS cutpercentage
            FROM filtered_responses fr
            JOIN {responses_table} r ON fr.participant_id = r.participant_id
            GROUP BY question_code
        ),
        average_answer AS (
            SELECT
                question_code,
                ROUND(AVG(CASE WHEN LOWER(response_text) = 'yes' THEN 1 ELSE 0 END) * 100.0) AS avg_yes_percentage
            FROM {responses_table}
            WHERE LOWER(response_text) IN ('yes', 'no')
            GROUP BY question_code
        )

        SELECT 
            qm.question_code,
            qm.q_question_code AS q_question_code,
            qm.s_question_text AS s_question_text, 
            CASE 
                WHEN LENGTH(qm.question_text) > 60 THEN CONCAT(LEFT(qm.question_text, 60), '...')
                ELSE qm.question_text
            END AS question_text,
            qm.answer_text AS answer_text,
            CONCAT(cp.cutpercentage, '%') AS cutpercentage,
            CONCAT(aa.avg_yes_percentage, '%') AS avg_yes_percentage,
            CASE 
                WHEN aa.avg_yes_percentage = 0 THEN NULL
                ELSE ROUND((cp.cutpercentage / aa.avg_yes_percentage) * 100)
            END AS `index`
        FROM cut_percentage cp
        JOIN average_answer aa ON cp.question_code = aa.question_code
        JOIN {question_mapping_table} qm ON cp.question_code = qm.question_code
        ORDER BY 
            CASE 
                WHEN qm.q_question_code IN ('Q27', 'Q28', 'Q29', 'Q30', 'Q31', 'Q32', 'Q33', 'Q34', 'Q35', 'Q36', 'Q37', 'Q38', 'Q39') THEN `index`
                ELSE CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(qm.question_code, 'Q', -1), '_', 1) AS UNSIGNED)
            END DESC, 
            qm.question_code;
        """
    else:
        query = "SELECT * FROM responses_1 WHERE 1=0"

    df = pd.read_sql(query, connection) 
    return df, sample_size


# Plot bar chart with editable labels
def plot_bar_chart_with_editable_labels(filtered_df, display_cut_percentage, display_avg_yes, display_index, bar_color_cut, bar_color_yes, bar_color_index, orientation):
    st.subheader("Edit Chart Labels and Title")

    # Editable chart title
    chart_title = st.text_input("Edit Bar Chart Title", value="Bar Chart Visualization")

    # Editable legend labels
    legend_cut_percentage = st.text_input("Legend for Data Cut Percentages", value="Data Cut Percentages")
    legend_avg_yes = st.text_input("Legend for Total Sample Percentages", value="Total Sample Percentages")
    legend_index = st.text_input("Legend for Index", value="Index")

    # Editable bar labels
    edited_labels = []
    cols = st.columns(2)  # Creates two columns

    for i, row in enumerate(filtered_df.itertuples(), 1):
        with cols[(i - 1) % 2]:  # Alternates between the two columns
            edited_label = st.text_input(
                f"Edit label for '{row.answer_text}'", 
                value=row.answer_text,
                key=f"label_input_{i}"
            )
        edited_labels.append(edited_label)


    filtered_df["edited_text"] = edited_labels

    max_chars_per_line = 30
    filtered_df["wrapped_text"] = filtered_df["edited_text"].apply(
        lambda text: textwrap.fill(text, width=max_chars_per_line)
    )

    # Sorting by selected metric
    sort_column = None
    if display_cut_percentage:
        sort_column = 'cutpercentage_numeric'
    elif display_avg_yes:
        sort_column = 'avg_yes_percentage_numeric'
    elif display_index:
        sort_column = 'index'
    if not sort_column:
        sort_column = 'avg_yes_percentage_numeric'
    
    filtered_df.sort_values(by=sort_column, ascending=True, inplace=True)

    # Plot configuration
    num_metrics = sum([display_avg_yes, display_cut_percentage, display_index])
    bar_width = 0.7 / num_metrics
    fig, ax = plt.subplots(figsize=(12, 8))
    x_pos = range(len(filtered_df))

    y_max = 0
    if display_cut_percentage:
        y_max = max(y_max, filtered_df['cutpercentage_numeric'].max())
    if display_avg_yes:
        y_max = max(y_max, filtered_df['avg_yes_percentage_numeric'].max())
    if display_index:
        y_max = max(y_max, filtered_df['index'].max())

    y_limit = min(500, max(60, y_max + 15))

    if orientation == "Vertical":
        bar_shift = -bar_width * (num_metrics // 2)
        for metric, display, color, label in [
            ("cutpercentage_numeric", display_cut_percentage, bar_color_cut, legend_cut_percentage),
            ("avg_yes_percentage_numeric", display_avg_yes, bar_color_yes, legend_avg_yes),
            ("index", display_index, bar_color_index, legend_index),
        ]:
            if display:
                ax.bar(
                    [pos + bar_shift for pos in x_pos],
                    filtered_df[metric],
                    width=bar_width,
                    label=label,
                    color=color,
                )
                for i, v in enumerate(filtered_df[metric]):
                    ax.text(i + bar_shift, v + 1, f"{v:.0f}%" if metric != "index" else f"{v:.0f}", ha="center", fontsize=9)
                bar_shift += bar_width

        ax.set_ylabel(" ")
        ax.set_title(chart_title, fontweight='bold')
        plt.xticks(x_pos, filtered_df["wrapped_text"], rotation=45, ha="right")
        ax.set_yticks([])
    else:
        bar_shift = -bar_width * (num_metrics // 2)
        for metric, display, color, label in [
            ("cutpercentage_numeric", display_cut_percentage, bar_color_cut, legend_cut_percentage),
            ("avg_yes_percentage_numeric", display_avg_yes, bar_color_yes, legend_avg_yes),
            ("index", display_index, bar_color_index, legend_index),
        ]:
            if display:
                ax.barh(
                    [pos + bar_shift for pos in x_pos],
                    filtered_df[metric],
                    height=bar_width,
                    label=label,
                    color=color,
                )
                for i, v in enumerate(filtered_df[metric]):
                    ax.text(v + 1, i + bar_shift, f"{v:.0f}%" if metric != "index" else f"{v:.0f}", va="center", fontsize=9)
                bar_shift += bar_width

        ax.set_xlabel(" ")
        ax.set_title(chart_title, fontweight='bold')
        plt.yticks(x_pos, filtered_df["wrapped_text"])
        ax.set_xticks([])
    ax.set_ylim(0, y_limit) if orientation == "Vertical" else ax.set_xlim(0, y_limit)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.015), ncol=3)
    st.pyplot(fig)

import altair as alt

def plot_el_bar_chart_with_editable_labels(el_display_df, orientation):
    if el_display_df.empty:
        return

    # Add color based on value
    def get_color(value):
        if value < 0:
            return "#DA261F"
        elif 1 <= value <= 3:
            return "#DAC41F"
        elif value > 3:
            return "#1FDA2C"
        else:
            return "#BDBDBD"  # default color for value = 0 or other cases
    
    el_display_df['Bar Color'] = el_display_df['Value'].apply(get_color)

    base = alt.Chart(el_display_df)
##Add option to sort the data by ascending or descending value with the deafult set to descending
    if orientation == "Horizontal":
# Horizontal chart
    
        bars = base.mark_bar().encode(
            y=alt.Y("EL Text:N", sort=el_display_df["EL Text"].tolist(), title=None, axis=alt.Axis(labelLimit=500)),
            x=alt.X("Value:Q", title="Value"),
            color=alt.Color("Bar Color:N", scale=None, legend=None)
        )

        labels = base.mark_text(
            align="left",
            baseline="middle",
            color="white",
            dx=3
        ).encode(
            y=alt.Y("EL Text:N", sort=el_display_df["EL Text"].tolist()),
            x="Value:Q",
            text=alt.Text("Value:Q", format=".0f")
        )

    else:  # Vertical
        bars = base.mark_bar().encode(
            x=alt.X("EL Text:N", sort=el_display_df["EL Text"].tolist(), title=None, axis=alt.Axis(labelLimit=200)),
            y=alt.Y("Value:Q", title="Value"),
            color=alt.Color("Bar Color:N", scale=None, legend=None)
        )

        labels = base.mark_text(
            align="center",
            baseline="bottom",
            dy=-3
        ).encode(
            x=alt.X("EL Text:N", sort=el_display_df["EL Text"].tolist()),
            y="Value:Q",
            text=alt.Text("Value:Q", format=".0f")
        )

    st.altair_chart((bars + labels).properties(height=600, width=800), use_container_width=True)

# Main function
def main():
    connection = connect_to_db()
    # ---- EL RESPONSES SECTION ----

# Connect to DB
    connection = connect_to_db()
    st.markdown(
    """
    <div style="text-align: center;">
        <h1 style="font-size: 38px; margin: 0; padding: 0;">GreenlightIQ</h1>
        <h2 style="font-size: 28px; margin: 0; padding: 0;">
            <em>"Fueling Creative Brilliance"</em> 
        </h2>
    </div>
    """,
        unsafe_allow_html=True
    )

# Fetch all question_codes for dropdown
   # =========================
# EL SECTION
# =========================

    el_question_codes_query = f"""
    SELECT DISTINCT question_code, answer_text
    FROM {FE_responses_table}
    ORDER BY question_code
    """
    el_question_codes_df = pd.read_sql(el_question_codes_query, connection)

    ##Build label → value mapping
    el_label_to_code = {
        f"{row['question_code']} {row['answer_text']}": row['question_code']
        for _, row in el_question_codes_df.iterrows()
    }
    
    # Build question_code to answer_text mapping for headers
    el_code_to_answer = {
        row['question_code']: row['answer_text']
        for _, row in el_question_codes_df.iterrows()
    }

# Dropdown labels - allow multiple selection
    el_dropdown_options = ["Select a Question Code"] + list(el_label_to_code.keys())

    selected_labels = st.multiselect(
        "Select up to 5 question codes for front end data:",
        el_dropdown_options,
        max_selections=5
    )

# Resolve actual question_codes
    selected_el_question_codes = [
        el_label_to_code[label]
        for label in selected_labels
        if label != "Select a Question Code"
    ]

    if selected_el_question_codes:

    # Fetch EL mapping (get once)
        el_mapping_query = f"""
        SELECT el_code, el_text, el_category, el_question
        FROM {FE_EL_mapping_table}
        ORDER BY el_order
        """
        el_mapping_df = pd.read_sql(el_mapping_query, connection)

        # -------------------------
        # Build combined comparison table
        # -------------------------
        comparison_data = {}
        
        for selected_el_question_code in selected_el_question_codes:
            # Fetch EL1–EL24 values for the selected question_code
            el_values_query = f"""
            SELECT *
            FROM {FE_responses_table}
            WHERE question_code = %s
            LIMIT 1
            """
            el_values_df = pd.read_sql(
                el_values_query,
                connection,
                params=[selected_el_question_code]
            )

            if not el_values_df.empty:
                values_dict = {}
                # Iterate through all EL codes from the mapping table
                for _, el_row in el_mapping_df.iterrows():
                    el_column = el_row["el_code"]
                    if el_column in el_values_df.columns:
                        values_dict[el_column] = el_values_df.iloc[0][el_column]
                
                comparison_data[selected_el_question_code] = values_dict

        # Create combined comparison dataframe
        if comparison_data:
            combined_rows = []
            # Iterate through all EL codes from the mapping table
            for _, el_row in el_mapping_df.iterrows():
                el_column = el_row["el_code"]
                el_text = el_row["el_text"]
                
                # Create row with EL info and values from each question
                row_data = {
                    "EL": el_column,
                    "EL Text": el_text
                }
                
                # Add values for each selected question code
                for j, question_code in enumerate(selected_el_question_codes):
                    if question_code in comparison_data:
                        answer_text = el_code_to_answer.get(question_code, "")
                        row_data[f"({question_code}) {answer_text}"] = comparison_data[question_code].get(el_column, None)
                
                combined_rows.append(row_data)

            combined_df = pd.DataFrame(combined_rows)
            
            # Display combined comparison table with server-side sorting
            st.markdown(f"### 📊 Front End Statements - {dataset_option}")
            
            # Display EL question text above the table
            if selected_el_question_codes:
                for question_code in selected_el_question_codes:
                    answer_text = el_code_to_answer.get(question_code, "")
                    # Get question_text from FE_responses table
                    question_text_query = f"""
                    SELECT DISTINCT question_text
                    FROM {FE_responses_table}
                    WHERE question_code = %s
                    LIMIT 1
                    """
                    question_text_df = pd.read_sql(question_text_query, connection, params=[question_code])
                    question_text = question_text_df.iloc[0]['question_text'] if not question_text_df.empty else ""
                    st.markdown(f"**{question_code} - {answer_text} - {question_text}**")
            
            # Calculate and display cumulative scores above the table
            cumulative_html = """
            <style>
            .cumulative-container {
                margin: 10px 0;
                padding: 10px;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                background-color: transparent;
            }
            .cumulative-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 14px;
                font-weight: bold;
            }
            .cumulative-table th, .cumulative-table td {
                padding: 8px;
                text-align: center;
                border: 1px solid #dee2e6;
            }
            .cumulative-table th {
                background-color: #e9ecef;
                color: #000;
            }
            .cell-red { background-color: #DA261F; color: white; font-weight: bold; }
            .cell-yellow { background-color: #DAC41F; color: black; font-weight: bold; }
            .cell-green { background-color: #1FDA2C; color: black; font-weight: bold; }
            </style>
            <div class="cumulative-container">
                <table class="cumulative-table">
                    <tr>
                        <th>Cumulative Score</th>
            """
            
            for question_code in selected_el_question_codes:
                answer_text = el_code_to_answer.get(question_code, "")
                col_name = f"({question_code}) {answer_text}"
                cumulative_html += f"<th>({question_code}) {answer_text}</th>"
            
            # Set the score label based on dataset
            if dataset_option == "Sports Fandom Study":
                score_label = "Olympian Engagement Score"
            elif dataset_option == "Shark Tank Study":
                score_label = "Driven to Watch Shark Tank Score"
            else:
                score_label = "Cumulative Score"
            
            cumulative_html += f"</tr><tr><td>{score_label}</td>"
            
            for question_code in selected_el_question_codes:
                answer_text = el_code_to_answer.get(question_code, "")
                col_name = f"({question_code}) {answer_text}"
                
                # Calculate sum of all EL values for this question
                cumulative_sum = 0
                for _, row in combined_df.iterrows():
                    value = row[col_name]
                    if not pd.isna(value):
                        cumulative_sum += value
                
                # Get the constant value from the FE_responses table for this question_code
                constant_query = f"""
                SELECT constant
                FROM {FE_responses_table}
                WHERE question_code = %s
                LIMIT 1
                """
                constant_df = pd.read_sql(constant_query, connection, params=[question_code])
                constant_value = constant_df.iloc[0]['constant'] if not constant_df.empty and 'constant' in constant_df.columns else 0
                
                # Add constant to the sum
                total_score = cumulative_sum + constant_value
                
                # Apply color coding based on total score
                if total_score < 130:
                    color_class = "cell-red"
                elif 130 <= total_score <= 150:
                    color_class = "cell-yellow"
                else:  # total_score >= 151
                    color_class = "cell-green"
                
                cumulative_html += f'<td class="{color_class}">{total_score:.0f}</td>'
            
            cumulative_html += "</tr></table></div>"
            st.markdown(cumulative_html, unsafe_allow_html=True)
            
            # Add sorting controls
            col1, col2 = st.columns([2, 1])
            with col1:
                # Default to first selected question code
                sort_options = ["EL", "EL Text"] + [f"({qc}) {el_code_to_answer.get(qc, '')}" for qc in selected_el_question_codes]
                default_sort = f"({selected_el_question_codes[0]}) {el_code_to_answer.get(selected_el_question_codes[0], '')}" if selected_el_question_codes else "EL"
                default_index = sort_options.index(default_sort) if default_sort in sort_options else 0
                sort_column = st.selectbox(
                    "Sort by:",
                    sort_options,
                    key="sort_column",
                    index=default_index
                )
            with col2:
                sort_direction = st.radio(
                    "Direction:",
                    ["Ascending", "Descending"],
                    key="sort_direction",
                    horizontal=True,
                    index=1  # Default to Descending
                )
            
            # Apply sorting
            if sort_column in combined_df.columns:
                if sort_column.startswith("("):
                    # Numeric sorting for value columns (columns that start with parentheses)
                    combined_df_sorted = combined_df.sort_values(
                        by=sort_column, 
                        ascending=(sort_direction == "Ascending"),
                        na_position='last'
                    )
                else:
                    # Text sorting for EL and EL Text columns
                    combined_df_sorted = combined_df.sort_values(
                        by=sort_column, 
                        ascending=(sort_direction == "Ascending"),
                        na_position='last'
                    )
            else:
                combined_df_sorted = combined_df
            
            # Create styled HTML table
            table_html = """
            <style>
            .comparison-table {
                width: 100%;
                border-collapse: collapse;
                margin: 5px 0;
                font-size: 13px;
            }
            .comparison-table th, .comparison-table td {
                border: 1px solid #ddd;
                padding: 2px 8px;
                text-align: center;
            }
            .comparison-table th {
                font-weight: bold;
                font-size: 11px;
                background-color: transparent;
            }
            .comparison-table td:first-child {
                text-align: left;
                width: 80px;
            }
            .comparison-table td:nth-child(2) {
                text-align: left;
                width: 365px;
                max-width: 450px;
            }
            .cell-red { background-color: #DA261F; color: black; }
            .cell-yellow { background-color: #DAC41F; color: black; }
            .cell-green { background-color: #1FDA2C; color: black; }
            .cell-gray { background-color: #BDBDBD; color: black; }
            </style>
            <table class="comparison-table">
            """
            
            # Add header
            el_question_header = el_mapping_df.iloc[0]['el_question'] if 'el_question' in el_mapping_df.columns else "EL Question"
            table_html += f"<tr><th>EL</th><th>{el_question_header}</th>"
            for question_code in selected_el_question_codes:
                answer_text = el_code_to_answer.get(question_code, "")
                table_html += f"<th>({question_code}) {answer_text}</th>"
            table_html += "</tr>"
            
            # Add data rows (sorted)
            for idx, row in combined_df_sorted.iterrows():
                table_html += "<tr>"
                table_html += f"<td>{row['EL']}</td>"
                # All rows show el_text
                table_html += f"<td>{row['EL Text']}</td>"
                
                for question_code in selected_el_question_codes:
                    answer_text = el_code_to_answer.get(question_code, "")
                    col_name = f"({question_code}) {answer_text}"
                    value = row[col_name]
                    
                    if pd.isna(value):
                        table_html += f'<td>-</td>'
                    else:
                        color_class = ""
                        if value < 0:
                            color_class = "cell-red"
                        elif 1 <= value <= 3:
                            color_class = "cell-yellow"
                        elif value > 3:
                            color_class = "cell-green"
                        else:
                            color_class = "cell-gray"
                        
                        table_html += f'<td class="{color_class}">{value:.0f}</td>'
                
                table_html += "</tr>"
            
            table_html += "</table>"
            
            st.markdown(table_html, unsafe_allow_html=True)

        # -------------------------
        # EL Category Summary Table
        # -------------------------
        if comparison_data and 'el_category' in el_mapping_df.columns:
            st.markdown(f"### 📊 EL Category Summary - {dataset_option}")
            
            # Calculate sums by category for each question
            category_summary = {}
            
            for question_code in selected_el_question_codes:
                if question_code in comparison_data:
                    category_sums = {}
                    for _, el_row in el_mapping_df.iterrows():
                        el_code = el_row["el_code"]
                        el_category = el_row["el_category"]
                        el_value = comparison_data[question_code].get(el_code, 0)
                        
                        if el_category not in category_sums:
                            category_sums[el_category] = 0
                        category_sums[el_category] += el_value if not pd.isna(el_value) else 0
                    
                    answer_text = el_code_to_answer.get(question_code, "")
                    category_summary[f"({question_code}) {answer_text}"] = category_sums
            
            # Create summary dataframe
            if category_summary:
                summary_rows = []
                all_categories = set()
                for col_data in category_summary.values():
                    all_categories.update(col_data.keys())
                
                for category in sorted(all_categories):
                    row_data = {"Category": category}
                    for col_name in category_summary.keys():
                        row_data[col_name] = category_summary[col_name].get(category, 0)
                    summary_rows.append(row_data)
                
                summary_df = pd.DataFrame(summary_rows)
                
                # Add sorting controls for summary table
                col1, col2 = st.columns([2, 1])
                with col1:
                    summary_sort_column = st.selectbox(
                        "Sort summary by:",
                        ["Category"] + list(category_summary.keys()),
                        key="summary_sort_column"
                    )
                with col2:
                    summary_sort_direction = st.radio(
                        "Summary Direction:",
                        ["Ascending", "Descending"],
                        key="summary_sort_direction",
                        horizontal=True
                    )
                
                # Apply sorting to summary table
                if summary_sort_column in summary_df.columns:
                    if summary_sort_column == "Category":
                        summary_df_sorted = summary_df.sort_values(
                            by=summary_sort_column,
                            ascending=(summary_sort_direction == "Ascending"),
                            na_position='last'
                        )
                    else:
                        # Numeric sorting for value columns
                        summary_df_sorted = summary_df.sort_values(
                            by=summary_sort_column,
                            ascending=(summary_sort_direction == "Ascending"),
                            na_position='last'
                        )
                else:
                    summary_df_sorted = summary_df
                
                # Create styled HTML summary table
                summary_html = """
                <style>
                .summary-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 5px 0;
                    font-size: 13px;
                }
                .summary-table th, .summary-table td {
                    border: 1px solid #ddd;
                    padding: 2px 8px;
                    text-align: center;
                }
                .summary-table th {
                    font-weight: bold;
                    font-size: 11px;
                    background-color: transparent;
                }
                .summary-table td:first-child {
                    text-align: left;
                    font-weight: bold;
                }
                </style>
                <table class="summary-table">
                """
                
                # Add header
                summary_html += "<tr><th>Category</th>"
                for col_name in category_summary.keys():
                    summary_html += f"<th>{col_name}</th>"
                summary_html += "</tr>"
                
                # Add data rows
                for _, row in summary_df_sorted.iterrows():
                    summary_html += "<tr>"
                    summary_html += f"<td>{row['Category']}</td>"
                    
                    for col_name in category_summary.keys():
                        value = row[col_name]
                        # Apply conditional coloring for summary values
                        color_class = ""
                        if value < 0:
                            color_class = "cell-red"
                        elif 1 <= value <= 3:
                            color_class = "cell-yellow"
                        elif value > 3:
                            color_class = "cell-green"
                        else:
                            color_class = "cell-gray"
                        
                        summary_html += f'<td class="{color_class}">{value:.0f}</td>'
                    
                    summary_html += "</tr>"
                
                summary_html += "</table>"
                st.markdown(summary_html, unsafe_allow_html=True)
        
        # Add button for generating backend data cut for each selected EL question
        if selected_el_question_codes:
            for question_code in selected_el_question_codes:
                answer_text = el_code_to_answer.get(question_code, "")
                button_text = f"Generate {answer_text} Backend"
                
                if st.button(button_text, key=f"backend_btn_{question_code}"):
                    # Generate data cut for this question_code
                    with st.spinner(f"Generating data cut for {question_code} - {answer_text}..."):
                        try:
                            # Use the existing fetch_data_and_sample_size function
                            df, sample_size = fetch_data_and_sample_size(connection, [question_code])
                            
                            if not df.empty:
                                # Store in session state to persist across reruns
                                st.session_state[f'backend_df_{question_code}'] = df
                                st.session_state[f'backend_sample_{question_code}'] = sample_size
                                st.session_state[f'backend_answer_text_{question_code}'] = answer_text
                            else:
                                st.warning(f"No data found for question code: {question_code}")
                        except Exception as e:
                            st.error(f"Error generating data cut: {str(e)}")
        
        # Display data cut if it exists in session state
        for question_code in selected_el_question_codes:
            if f'backend_df_{question_code}' in st.session_state:
                df = st.session_state[f'backend_df_{question_code}']
                sample_size = st.session_state[f'backend_sample_{question_code}']
                answer_text = st.session_state[f'backend_answer_text_{question_code}']
                
                st.markdown(f"### 📊 Data Cut - {question_code} - {answer_text}")
                st.write(f"Sample Size = {sample_size}")
                st.write("Data fetched from MySQL:")
                st.dataframe(df)

                df['cutpercentage_numeric'] = df['cutpercentage'].str.replace('%', '').astype(float)
                df['avg_yes_percentage_numeric'] = df['avg_yes_percentage'].str.replace('%', '').astype(float)

                # Create dropdown labels for this data cut
                df['dropdown_label'] = df['answer_text'] + ",   " + df['question_code'] + ",   " + df['question_text']
                
                # Get unique q_question_codes for selection (like original)
                unique_q_question_codes = df[['q_question_code', 's_question_text']].drop_duplicates()
                q_question_code_mapping = {
                    f"{row.q_question_code} - {row.s_question_text}": row.q_question_code
                    for row in unique_q_question_codes.itertuples()
                }
                
                # Create dropdown options list
                q_question_code_options = ["No Question Code"] + list(q_question_code_mapping.keys())
                
                # Select Question Codes
                selected_q_question_codes_display = st.multiselect(
                    f"Optional: Select Question Codes to Auto-Select Answers for {answer_text}:",
                    q_question_code_options,
                    key=f"backend_q_codes_{question_code}"
                )
                
                # Convert selected display values back to actual q_question_code
                selected_q_question_codes = [
                    q_question_code_mapping[option] for option in selected_q_question_codes_display if option != "No Question Code"
                ]
                
                # Auto-select answers based on selected q_question_codes
                if selected_q_question_codes:
                    auto_selected_answers = df[
                        df['q_question_code'].isin(selected_q_question_codes)
                    ]['dropdown_label'].tolist()
                else:
                    auto_selected_answers = []
                
                # Bar Chart Answer Selection (with auto-selected answers)
                selected_answers = st.multiselect(
                    f"Select answers to display in the bar chart for {answer_text}:",
                    df['dropdown_label'].tolist(),
                    default=auto_selected_answers,
                    key=f"backend_answers_{question_code}"
                )

                st.subheader(f"Bar Chart Visualization - {answer_text}")
                
                # Chart controls - exactly like original
                display_avg_yes = st.checkbox("Display Total Sample Percentages", value=False, key=f"backend_avg_yes_{question_code}")
                display_cut_percentage = st.checkbox("Display Data Cut Percentages", value=True, key=f"backend_cut_{question_code}")
                display_index = st.checkbox("Display Index", value=False, key=f"backend_index_{question_code}")

                bar_color_cut = st.color_picker("Pick a Bar Color for Data Cut Percentages", "#0F0FE4", key=f"backend_color_cut_{question_code}")
                bar_color_yes = st.color_picker("Pick a Bar Color for Total Sample Percentages", "#B50C0C", key=f"backend_color_yes_{question_code}")
                bar_color_index = st.color_picker("Pick a Bar Color for Index", "#2ca02c", key=f"backend_color_index_{question_code}")
                orientation = st.radio("Choose Chart Orientation", ["Vertical", "Horizontal"], index=1, key=f"backend_orient_{question_code}")

                if selected_answers:
                    selected_question_codes = df[
                        df['dropdown_label'].isin(selected_answers)
                    ]['question_code'].tolist()

                    filtered_df = df[df['question_code'].isin(selected_question_codes)]

                    plot_bar_chart_with_editable_labels(
                        filtered_df,
                        display_cut_percentage,
                        display_avg_yes,
                        display_index,
                        bar_color_cut,
                        bar_color_yes,
                        bar_color_index,
                        orientation
                    )
                else:
                    st.write(f"Please select answers to display on the bar chart for {answer_text}.")

        # Process each selected question code for individual charts
        for idx, selected_el_question_code in enumerate(selected_el_question_codes):
            st.markdown(f"### EL Bar Chart - Question {idx + 1}: {selected_el_question_code} - {el_code_to_answer.get(selected_el_question_code, '')}")
            
            # Fetch EL1–EL24 values for the selected question_code
            el_values_query = f"""
            SELECT *
            FROM {FE_responses_table}
            WHERE question_code = %s
            LIMIT 1
            """
            el_values_df = pd.read_sql(
                el_values_query,
                connection,
                params=[selected_el_question_code]
            )

            if not el_values_df.empty:
                # -------------------------
                # Build display dataframe
                # -------------------------
                rows = [] 

                # Iterate through all EL codes from the mapping table
                for _, el_row in el_mapping_df.iterrows():
                    el_column = el_row["el_code"]

                    if el_column in el_values_df.columns:
                        el_value = el_values_df.iloc[0][el_column]
                        el_text = el_row["el_text"]
                    else:
                        el_value = None
                        el_text = el_row["el_text"]

                    rows.append({
                        "EL": el_column,
                        "EL Text": el_text,
                        "Value": el_value
                    })

                display_df = pd.DataFrame(rows)

            # -------------------------
            # EL BAR CHART CONTROLS
            # -------------------------
                st.markdown(f"#### Chart Controls - Question {idx + 1}")

                el_orientation = st.radio(
                    f"EL Chart Orientation - Question {idx + 1}",
                    ["Vertical", "Horizontal"],
                    index=1,
                    horizontal=True,
                    key=f"el_orientation_{idx}"
                )
                
                # EL Sort Controls
                el_sort_col1, el_sort_col2, el_sort_col3 = st.columns([1, 1, 2])
                
                with el_sort_col1:
                    el_sort_enabled = st.checkbox("Enable Sorting", key=f"el_sort_enabled_{idx}")
                
                with el_sort_col2:
                    if el_sort_enabled:
                        el_sort_order = st.radio(
                            "Sort Order",
                            ["Ascending", "Descending"],
                            key=f"el_sort_order_{idx}"
                        )
                
                with el_sort_col3:
                    if el_sort_enabled:
                        el_sort_by = st.selectbox(
                            "Sort By",
                            ["Value", "EL Text"],
                            key=f"el_sort_by_{idx}"
                        )

                # -------------------------
                # EL BAR CHART
                # -------------------------
                # Apply sorting if enabled
                el_display_df = display_df.copy()
                if el_sort_enabled:
                    if el_sort_by == "Value":
                        el_display_df = el_display_df.sort_values(
                            by="Value", 
                            ascending=(el_sort_order == "Ascending")
                        ).reset_index(drop=True)
                    else:  # Sort by EL Text
                        el_display_df = el_display_df.sort_values(
                            by="EL Text", 
                            ascending=(el_sort_order == "Ascending")
                        ).reset_index(drop=True)
                
                el_display_df["EL Text Ordered"] = pd.Categorical(
                    el_display_df["EL Text"],
                    categories=el_display_df["EL Text"],  # preserves sorted order
                    ordered=True
                )
                
                plot_el_bar_chart_with_editable_labels(
                    el_display_df,
                    orientation=el_orientation
                )

                st.markdown("---")  # Add separator between charts

            else:
                st.write(f"No EL data found for question code: {selected_el_question_code}")

    else:
        st.write("Please select at least one question code.")

    # Apply custom theme
    apply_custom_theme()

    connection = connect_to_db()

    # Fetch categories
    category_query = f"""
    SELECT DISTINCT question_category FROM {question_mapping_table}
    ORDER BY question_category
    """
    category_df = pd.read_sql(category_query, connection)
    categories = ["All Categories"] + category_df['question_category'].tolist()

    # Category dropdown
    selected_category = st.selectbox("Select a Category:", categories)

    # Fetch question data based on the selected category
    question_query = f"""
    SELECT question_code, answer_text, question_text, q_question_code
    FROM {question_mapping_table}
    WHERE question_category LIKE '{selected_category}' OR '{selected_category}' = 'All Categories'
    ORDER BY CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(question_code, 'Q', -1), '_', 1) AS UNSIGNED), question_code
    """
    question_df = pd.read_sql(question_query, connection)

    question_query_all = f"""
    SELECT question_code, answer_text, question_text, q_question_code, s_question_text, question_category AS category
    FROM {question_mapping_table}
    ORDER BY CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(question_code, 'Q', -1), '_', 1) AS UNSIGNED), question_code
    """
    question_df_all = pd.read_sql(question_query_all, connection)

    question_df['dropdown_label'] = question_df['answer_text'] + ", [" + question_df['question_code'] + "],   " + question_df['question_text']
    question_df_all['dropdown_label'] = question_df_all['answer_text'] + ",   " + question_df_all['question_code'] + ",   " + question_df_all['question_text']

    question_options = ["No Answer"] + question_df['dropdown_label'].tolist()

    question_selected_1 = st.selectbox("Select a Question (Optional):", question_options)
    question_selected_2 = st.selectbox("Select a Second Question (Optional):", question_options)
    question_selected_3 = st.selectbox("Select a Third Question (Optional):", question_options)

    selected_questions = [
        question_df[question_df['dropdown_label'] == q]['question_code'].values[0]
        for q in [question_selected_1, question_selected_2, question_selected_3]
        if q != "No Answer"
    ]
    with st.expander("See detailed explanation"):
        st.write("""
        What is a data cut?
        A data cut is our way of isolating audiences to reveal insights about their habits and preferences. We do this by first choosing people who selected yes to certain answers in this study to then look at the performance of other answers. In the first section of our tool, you select the answer or answers to define the group you are trying to isolate. Once selected, the rest of the answers appear below displaying the percentage of people who selected yes to each answer from the whole study sample (Total Sample Percentage) next to the percentage of people who selected yes to each answer from the group you isolated (Cut Percentage). In the last column, index is displayed.

        Glossary:
        
        Total Sample Percentage: Used for defining the performance of an answer with all respondents.

        Cut Percentage: Used for defining the performance of an answer with a selected audience.
           
        Index: Used to compare the performance of an answer with a selected audience to its performance with all respondents.


        Formulas: 
                      
        Total Sample Percentage = (# of people who selected yes to that answer)/(Total study sample size)

        Cut Percentage = (# of people who said yes to both that answer and the answer(s) chosen in the first drop down menus)/(# of people who said yes to the answer(s) chosen in the first drop down menu)

        Index = (Cut Percentage)/(Total Sample Percentage) * 100 
                 
        (If index = 100, then equal performance with selected audience and all respondents)
    """)
    # Fetch data and sample size after questions are selected
    if selected_questions:
        df, sample_size = fetch_data_and_sample_size(connection, selected_questions)
        st.write(f"Sample Size = {sample_size}")

        if not df.empty:
            st.write("Data fetched from MySQL:")
            st.dataframe(df)

            df['cutpercentage_numeric'] = df['cutpercentage'].str.replace('%', '').astype(float)
            df['avg_yes_percentage_numeric'] = df['avg_yes_percentage'].str.replace('%', '').astype(float)

            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)

            st.download_button(
                label="Download CSV",
                data=csv_buffer.getvalue(),
                file_name="exported_data.csv",
                mime="text/csv"
            )
             
            # ---- Generate Dashboard Button ----
            
            # Button that sets session state
            if st.button("Generate Dashboard"):
                st.session_state['show_dashboard'] = True

# Persist dashboard on interactions
            if st.session_state.get('show_dashboard', False):
    

              # ---- DEMOGRAPHICS SECTION ----  
                demo_df = df[df['question_code'].isin(
                    question_df_all[question_df_all['category'] == 'Demographics']['question_code']
                )]

                if not demo_df.empty:
                    st.markdown("### 👥 Demographics")
                    unique_q_codes = demo_df['q_question_code'].unique()

                    for i in range(0, len(unique_q_codes), 2):  # 2 columns per row
                        row_q_codes = unique_q_codes[i:i + 2]
                        cols = st.columns(2)

                        for col, q_code in zip(cols, row_q_codes):
                            subset = demo_df[demo_df['q_question_code'] == q_code].nlargest(5, 'cutpercentage_numeric')
                            if not subset.empty:
                                s_question_text = subset['s_question_text'].iloc[0] if 's_question_text' in subset.columns else ""
                                with col:
                                    st.write(f"**{q_code}: {s_question_text}**")
                                    st.dataframe(subset[['answer_text', 'cutpercentage', 'index']].reset_index(drop=True),
                                                height = 210
                                                )
                    # --- Select Metric ---
                                    metric_col, chart_col = st.columns(2)

                                    with metric_col:
                                        st.markdown("**Select Metric**")
                                        metric_cut = st.checkbox("Cut Percentage", value=True, key=f"metric_cut_{q_code}")
                                        metric_index = st.checkbox("Index", value=False, key=f"metric_index_{q_code}")

                                    with chart_col:
                                        st.markdown("**Select Chart**")
                                        show_bar = st.checkbox("Bar Chart", key=f"bar_{q_code}")
                                        show_pie = st.checkbox("Pie Chart", key=f"pie_{q_code}")
                    # Determine selected metric (prioritize cut > avg > index)
                                    if metric_cut:
                                        metric = 'cutpercentage_numeric'
                                    elif metric_index:
                                        metric = 'index'
                                    else:
                                        metric = 'cutpercentage_numeric'  # fallback

                    # Render charts
                                    if show_bar:
                                        fig, ax = plt.subplots(figsize=(4, 3))  # smaller figure
                                        ax.barh(subset['answer_text'], subset[metric])
                                        ax.set_title(f"{q_code} - {s_question_text}")
                                        ax.set_xlabel(metric.replace("cutpercentage_numeric", "Cut Percentage").title())
                                        ax.set_ylabel("Answers")
                                        st.pyplot(fig)

                                    if show_pie:
                                        fig, ax = plt.subplots(figsize=(3, 4))  # smaller figure
                                        ax.pie(subset[metric], labels=subset['answer_text'], autopct="%1.1f%%")
                                        ax.set_title(f"{q_code} - {s_question_text}")
                                        st.pyplot(fig)



                # ---- CONTENT SECTION ----
                content_df = df[df['question_code'].isin(
                    question_df_all[question_df_all['category'] == 'Content']['question_code']
                )]

                if not content_df.empty:
                    st.markdown("### 📌 Content (Top 5 listed)")

    # ✅ 1. Define the question order you want
                    desired_order = ["Q15", "Q17", "Q16", "Q20", "Q5", "Q4"]

    # ✅ 2. Add a sorting key based on desired order
                    content_df['sort_order'] = content_df['q_question_code'].apply(
                        lambda x: desired_order.index(x) if x in desired_order else len(desired_order)
                    )

    # ✅ 3. Sort the dataframe by the custom order
                    content_df = content_df.sort_values(by='sort_order')

    # ✅ 4. Get q_question_code in sorted order
                    unique_q_codes = content_df['q_question_code'].unique()

                    for i in range(0, len(unique_q_codes), 3):
                        row_q_codes = unique_q_codes[i:i + 3]
                        cols = st.columns(3)

                        for col, q_code in zip(cols, row_q_codes):
                            subset = content_df[content_df['q_question_code'] == q_code].nlargest(5, 'cutpercentage_numeric')
                            if not subset.empty:
                                s_question_text = subset['s_question_text'].iloc[0] if 's_question_text' in subset.columns else ""
                                with col:
                                    st.write(f"**{q_code}: {s_question_text}**")
                                    df_to_display = subset[['answer_text', 'cutpercentage', 'index']].reset_index(drop=True)
                                    st.dataframe(df_to_display)

    # ---- BRANDS SECTION ----
                brands_df = df[df['question_code'].isin(
                    question_df_all[question_df_all['category'] == 'Brand']['question_code']
                )]
                if not brands_df.empty:
                    st.markdown("### 🏷️ Brands (Top 20)")
                    brands_top20 = brands_df.nlargest(20, 'index')
                    st.dataframe(brands_top20[['q_question_code', 'answer_text', 'cutpercentage', 'index']].reset_index(drop=True))
                    
            unique_q_question_codes = question_df_all[['q_question_code', 's_question_text']].drop_duplicates()
 
             # Create dropdown options as "q_question_code - s_question_text" (display) but store q_question_code for logic
            q_question_code_mapping = {
                 f"{row.q_question_code} - {row.s_question_text}": row.q_question_code
                 for row in unique_q_question_codes.itertuples()
             }
 
             # Create dropdown options list
            q_question_code_options = ["No Question Code"] + list(q_question_code_mapping.keys())
 
             # Select Question Codes
            selected_q_question_codes_display = st.multiselect(
                 "Optional: Select Question Codes to Auto-Select Answers:",
                 q_question_code_options
             )
 
             # Convert selected display values back to actual q_question_code
            selected_q_question_codes = [
                 q_question_code_mapping[option] for option in selected_q_question_codes_display if option != "No Question Code"
             ]
 
             # Auto-select answers based on selected q_question_codes
            if selected_q_question_codes:
                 auto_selected_answers = question_df_all[
                     question_df_all['q_question_code'].isin(selected_q_question_codes)
                 ]['dropdown_label'].tolist()
            else:
                 auto_selected_answers = []
 
             # Bar Chart Answer Selection (with auto-selected answers)
            selected_answers = st.multiselect(
                "Select answers to display in the bar chart:",
                question_df_all['dropdown_label'].tolist(),
                default=auto_selected_answers  # Auto-select answers if applicable
            )

            st.subheader("Bar Chart Visualization")


            
            display_avg_yes = st.checkbox("Display Total Sample Percentages", value=False)
            display_cut_percentage = st.checkbox("Display Data Cut Percentages", value=True)
            display_index = st.checkbox("Display Index", value=False)

            bar_color_cut = st.color_picker("Pick a Bar Color for Data Cut Percentages", "#0F0FE4")
            bar_color_yes = st.color_picker("Pick a Bar Color for Total Sample Percentages", "#B50C0C")
            bar_color_index = st.color_picker("Pick a Bar Color for Index", "#2ca02c")
            orientation = st.radio("Choose Chart Orientation", ["Vertical", "Horizontal"], index=1)

            if selected_answers:
                selected_question_codes = question_df_all[
                    question_df_all['dropdown_label'].isin(selected_answers)
                ]['question_code'].tolist()

                filtered_df = df[df['question_code'].isin(selected_question_codes)]

                plot_bar_chart_with_editable_labels(
                    filtered_df,
                    display_cut_percentage,
                    display_avg_yes,
                    display_index,
                    bar_color_cut,
                    bar_color_yes,
                    bar_color_index,
                    orientation
                )
            else:
                st.write("Please select answers to display on the bar chart.")
        else:
            st.write("No data found for selected questions.")
    else:
        st.write("Please select at least one question.")
    connection.close()
if __name__ == "__main__":
    main()
