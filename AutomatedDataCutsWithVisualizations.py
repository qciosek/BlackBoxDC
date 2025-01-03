import streamlit as st
import pymysql
import pandas as pd
import io
import matplotlib.pyplot as plt

# Clear Streamlit cache
st.cache_data.clear()

# Connect to the MySQL database
def connect_to_db():
    connection = pymysql.connect(
        host='localhost',
        user='quincyciosek',
        password='Omega1745!',
        database='study_data'
    )
    return connection

# Query to retrieve the data and calculate sample size
def fetch_data_and_sample_size(connection, selected_questions):
    # Prepare question code filter
    question_code_filter = "', '".join(selected_questions) if selected_questions else None
    
    # Query to get the sample size (distinct participant IDs)
    if question_code_filter:
        sample_size_query = f"""
        SELECT COUNT(DISTINCT participant_id) AS sample_size
        FROM responses
        WHERE question_code IN ('{question_code_filter}')
        """
    else:
        sample_size_query = "SELECT COUNT(DISTINCT participant_id) AS sample_size FROM responses"
    
    sample_size_df = pd.read_sql(sample_size_query, connection)
    sample_size = sample_size_df['sample_size'][0] if not sample_size_df.empty else 0

    # Query to retrieve the data based on selected questions
    if question_code_filter:
        query = f"""
        WITH filtered_responses AS (
            SELECT DISTINCT participant_id
            FROM responses
            WHERE participant_id IN (
                SELECT participant_id
                FROM responses
                WHERE question_code IN ('{question_code_filter}')
                AND response_text = 'Yes'
            )
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
        ORDER BY question_text, answer_text;
        """
    else:
        # If no questions are selected, return empty dataframe and sample size as 0
        return pd.DataFrame(), 0

    df = pd.read_sql(query, connection)
    return df, sample_size

# Streamlit app
def main():
    st.title("Fetch and Download Data")

    # Fetch the available question codes and answer texts for dropdown
    connection = connect_to_db()
    question_query = """
    SELECT question_code, answer_text 
    FROM question_mapping
    ORDER BY answer_text, question_code
    """
    question_df = pd.read_sql(question_query, connection)

    # Create a dropdown displaying answer_text, question_code (e.g., "Winter Olympics, Q4_M20")
    question_df['dropdown_label'] = question_df['answer_text'] + ", " + question_df['question_code']
    question_options = question_df['dropdown_label'].tolist()

    # Add "No Answer" option to the dropdown
    question_options = ["No Answer"] + question_options

    # Dropdown menus for selecting up to 3 questions
    question_selected_1 = st.selectbox("Select a Question (Optional):", question_options)
    question_selected_2 = st.selectbox("Select a Second Question (Optional):", question_options)
    question_selected_3 = st.selectbox("Select a Third Question (Optional):", question_options)

    # Prepare the selected question codes, excluding "No Answer"
    selected_questions = []
    for question_selected in [question_selected_1, question_selected_2, question_selected_3]:
        if question_selected != "No Answer":
            question_code = question_df[question_df['dropdown_label'] == question_selected]['question_code'].values[0]
            selected_questions.append(question_code)

    # Only fetch data and update sample size if at least one question is selected
    if selected_questions:
        df, sample_size = fetch_data_and_sample_size(connection, selected_questions)
        st.write(f"Sample Size = {sample_size}")
    else:
        st.write("Please select at least one question to calculate the sample size.")

    # Check if data exists for the selected questions
    if selected_questions and not df.empty:
        # Show the data with percentages as strings
        st.write("Data fetched from MySQL:")
        st.dataframe(df)

        # Convert 'cutpercentage' and 'avg_yes_percentage' columns for bar chart as numeric values (without '%')
        df['cutpercentage_numeric'] = df['cutpercentage'].str.replace('%', '').astype(float)
        df['avg_yes_percentage_numeric'] = df['avg_yes_percentage'].str.replace('%', '').astype(float)

        # Convert the DataFrame to CSV in memory
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        # Provide a download button
        st.download_button(
            label="Download CSV",
            data=csv_buffer.getvalue(),
            file_name="exported_data.csv",
            mime="text/csv"
        )

        # Select answers for the bar chart
        st.subheader("Bar Chart Visualization")
        selected_answers = st.multiselect(
            "Select up to 3 answers to display in the bar chart:",
            df['answer_text'].unique().tolist(),
            max_selections=3
        )

        # Display bar charts for selected answers
        if selected_answers:
            # Filter for selected answers
            filtered_df = df[df['answer_text'].isin(selected_answers)].drop_duplicates(subset=['answer_text'])

            # Set positions for adjacent bars
            bar_width = 0.4  # width of each bar
            answer_offset = 1  # separation between different answers

            fig, ax = plt.subplots(figsize=(10, 6))

            # Initialize the x position for the bars
            x_pos = range(len(filtered_df))

            # Plot the cut_percentage bars
            ax.bar(
                [pos - bar_width / 2 for pos in x_pos],  # shift left
                filtered_df['cutpercentage_numeric'],
                width=bar_width,
                label='Cut Percentage',
                color='blue'
            )

            # Plot the avg_yes_percentage bars
            ax.bar(
                [pos + bar_width / 2 for pos in x_pos],  # shift right
                filtered_df['avg_yes_percentage_numeric'],
                width=bar_width,
                label='Avg Yes Percentage',
                color='orange'
            )

            ax.set_ylabel('Percentage')
            ax.set_title('Cut Percentage vs Avg Yes Percentage')
            ax.set_ylim(0, 100)
            ax.legend()
            plt.xticks([pos for pos in x_pos], filtered_df['answer_text'], rotation=45, ha='right')

            st.pyplot(fig)

    elif selected_questions:
        st.write("No data found for the selected questions.")

if __name__ == "__main__":
    main()















