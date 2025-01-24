import streamlit as st
import pymysql
import pandas as pd
import io
import matplotlib.pyplot as plt
import textwrap

# Clear Streamlit cache
st.cache_data.clear()

# Connect to the MySQL database
def connect_to_db():
    connection = pymysql.connect(
        host='database-1.c5isyysu810z.us-east-2.rds.amazonaws.com',
        user='admin',
        password='Omega1745!',
        database='study_data',
        port=3306,
    )
    return connection

# Fetch data and sample size
def fetch_data_and_sample_size(connection, selected_questions):
    question_code_filter = "', '".join(selected_questions)
    if question_code_filter:
        # Calculate the sample size: Participants who said "Yes" to all selected questions
        sample_size_query = f"""
        SELECT COUNT(DISTINCT participant_id) AS sample_size
        FROM (
            SELECT participant_id
            FROM responses
            WHERE response_text = 'Yes'
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
            FROM responses
            WHERE response_text = 'Yes' 
            AND question_code IN ('{question_code_filter}')
            GROUP BY participant_id
            HAVING COUNT(DISTINCT question_code) = {len(selected_questions)}
        ),
        cut_percentage AS (
            SELECT 
                question_code,
                ROUND(COUNT(CASE WHEN response_text = 'Yes' THEN 1 END) * 100.0 / COUNT(*)) AS cutpercentage
            FROM filtered_responses fr
            JOIN responses r ON fr.participant_id = r.participant_id
            GROUP BY question_code
        ),
        average_answer AS (
            SELECT
                question_code,
                ROUND(AVG(CASE WHEN response_text = 'Yes' THEN 1 ELSE 0 END) * 100.0) AS avg_yes_percentage
            FROM responses
            GROUP BY question_code
        )
    
        SELECT 
            qm.question_code, 
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
        JOIN question_mapping qm ON cp.question_code = qm.question_code
        ORDER BY CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(qm.question_code, 'Q', -1), '_', 1) AS UNSIGNED), qm.question_code;
        """
    else:
        query = "SELECT * FROM responses WHERE 1=0"
            

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
    for i, row in filtered_df.iterrows():
        edited_label = st.text_input(
            f"Edit label for '{row['answer_text']}'", 
            value=row['answer_text'],
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

    filtered_df.sort_values(by=sort_column, ascending=True, inplace=True)

    # Plot configuration
    num_metrics = sum([display_avg_yes, display_cut_percentage, display_index])
    bar_width = 0.7 / num_metrics
    fig, ax = plt.subplots(figsize=(10, 6))
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

        ax.set_ylabel("Percentage")
        ax.set_title(chart_title)
        plt.xticks(x_pos, filtered_df["wrapped_text"], rotation=45, ha="right")
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

        ax.set_xlabel("Percentage")
        ax.set_title(chart_title)
        plt.yticks(x_pos, filtered_df["wrapped_text"])

    ax.set_ylim(0, y_limit) if orientation == "Vertical" else ax.set_xlim(0, y_limit)
    ax.legend()
    st.pyplot(fig)

# Main function
def main():
    st.title("World’s Greatest Data from Olympics Fandom Study")

    connection = connect_to_db()
    question_query = """
    SELECT question_code, answer_text, question_text 
    FROM question_mapping
    ORDER BY CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(question_code, 'Q', -1), '_', 1) AS UNSIGNED), question_code
    """
    question_df = pd.read_sql(question_query, connection)

    question_df['dropdown_label'] = question_df['answer_text'] + ", " + question_df['question_code'] + ", " + question_df['question_text']
    question_options = ["No Answer"] + question_df['dropdown_label'].tolist()

    question_selected_1 = st.selectbox("Select a Question (Optional):", question_options)
    question_selected_2 = st.selectbox("Select a Second Question (Optional):", question_options)
    question_selected_3 = st.selectbox("Select a Third Question (Optional):", question_options)

    selected_questions = [
        question_df[question_df['dropdown_label'] == q]['question_code'].values[0]
        for q in [question_selected_1, question_selected_2, question_selected_3]
        if q != "No Answer"
    ]

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

            st.subheader("Bar Chart Visualization")

            display_avg_yes = st.checkbox("Display Total Sample Percentages", value=True)
            display_cut_percentage = st.checkbox("Display Data Cut Percentages", value=True)
            display_index = st.checkbox("Display Index", value=False)

            selected_answers = st.multiselect(
                "Select answers to display in the bar chart:",
                question_df['dropdown_label'].tolist(),
            )

            bar_color_cut = st.color_picker("Pick a Bar Color for Data Cut Percentages", "#1f77b4")
            bar_color_yes = st.color_picker("Pick a Bar Color for Total Sample Percentages", "#ff7f0e")
            bar_color_index = st.color_picker("Pick a Bar Color for Index", "#2ca02c")
            orientation = st.radio("Choose Chart Orientation", ["Vertical", "Horizontal"])

            if selected_answers:
                selected_question_codes = question_df[
                    question_df['dropdown_label'].isin(selected_answers)
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
                st.write("Please select answers to display the bar chart.")
        else:
            st.write("No data found for the selected questions.")
    else:
        st.write("Please select questions to fetch data.")

if __name__ == "__main__":
    main()
