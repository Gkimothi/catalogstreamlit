from operator import index
import streamlit as st
import numpy as np
import pandas as pd
import altair as alt
import datetime as dt
from google.oauth2 import service_account
from gsheetsdb import connect
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import GridUpdateMode

# Create a connection object.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
    ],
)
conn = connect(credentials=credentials)
sheet_url = st.secrets["private_gsheets_url"]

# Use the full page instead of a narrow central column and some other essentials
st.set_page_config(
    page_title="My Books Catalog",
    page_icon="📚",
    layout="wide"
    )
# Set title - recommended practice
st.title('Reyansh\'s Year in Books') 

# Begin Get data
#@st.cache(ttl=600,allow_output_mutation=True) # Not working on Streamlit cloud
def get_data():
    query = f'SELECT * FROM "{sheet_url}"'
    return pd.read_sql(query, conn)
df = get_data()
# End Get data

# Begin dataframe manipulation for book read year month
df['ReadDate'] = pd.to_datetime(df['FinishDate'])
df['ReadYearMonth'] = df['ReadDate'].dt.strftime('%Y-%m')
df_yearmonth = df.groupby(['ReadYearMonth']).count()['BookName'].reset_index()
df_yearmonth.columns = ['ReadYearMonth', 'Count of Books']
# End dataframe manipulation

# Begin dataframe manipulation for category percentage
df_categories_percentage = df.groupby(['Category']).count()['BookName'].reset_index()
df_categories_percentage.columns = ['Category', 'Count of Books']
df_categories_percentage['Category Percentage'] = (df_categories_percentage['Count of Books']/(df_categories_percentage['Count of Books'].sum())*100).round(decimals=2)
# End dataframe manipulation

# Begin dataframe manipulation for books by category cumulative total over READYEARMONTH
df_crosstab_category = pd.crosstab(index=df['ReadYearMonth'], columns=df['Category'], rownames=['ReadYearMonth']).cumsum()
df_crosstab_cumcount_category = df_crosstab_category.stack().reset_index().rename(columns={0:'CummulativeCount'})
# End dataframe manipulation

col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
col1.metric("Number of Books", df.shape[0])
col2.metric("Number of Authors", df.Authors.nunique())
col3.metric("Most books in a month", df_yearmonth['Count of Books'].max())

fig_category_percent = alt.Chart(df_categories_percentage).mark_arc().encode(theta=alt.Theta('Category Percentage:Q'),
                                                        color= alt.Color('Category:N', legend=None),
                                                        tooltip=['Category:N', alt.Tooltip('Category Percentage:Q',
                                                         title='Percentage')]).configure_view(strokeWidth=0)
                                                        

with col4:
    st.altair_chart(fig_category_percent, use_container_width=True)

# Begin Display cumulative number of books read by category over time
fig_category_line = alt.Chart(df_crosstab_cumcount_category).mark_line(point=alt.OverlayMarkDef()).encode(alt.X('ReadYearMonth', axis=alt.Axis(title='Month-Year Read')),
                                                                                alt.Y('CummulativeCount:Q', axis=alt.Axis(title='Cumulative Count'),),
                                                                                tooltip=[alt.Tooltip('Category', title='Category'),
                                                                                alt.Tooltip('ReadYearMonth', title='Month'), alt.Tooltip('CummulativeCount:Q',
                                                                                title='Cumulative No. of Books'),],
                                                                                 color='Category').properties(height=500).interactive()
st.subheader("Cumulative Count by Category over Months")
st.altair_chart(fig_category_line, use_container_width=True)
# End Display cumulative number of books read by category over time

# Begin Display number of books read by category
click = alt.selection_single(fields=['Category'])
color=alt.condition(click, alt.Color('Category:N'), alt.value('lightgray'))
fig_category_count = alt.Chart(df).mark_bar().encode(alt.X('Category:N', sort='-y'),
                                                                alt.Y('count(BookName):Q', axis=alt.Axis(title='No. of Books')),
                                                                color=color,
                                                                tooltip=['Category:N', alt.Tooltip('count(BookName):Q',
                                                                 title='Number of Books')]).configure_view(strokeWidth=0).add_selection(click)
st.subheader("Books by Category")
st.altair_chart(fig_category_count, use_container_width=True)

# End Display number of books read by category

# Begin Display number of books by monthly buckets
# fig_books_yearmonth_count = alt.Chart(df).mark_bar().encode(alt.X('ReadYearMonth'), alt.Y('count(BookName):Q'),color='Category',
#                                                                     tooltip=[alt.Tooltip('ReadYearMonth', title='Month'), alt.Tooltip('count(BookName)', title='Number of Books'),])
#                                                                     #.transform_filter(click).interactive()
fig_books_yearmonth_count = alt.Chart(df).mark_bar().encode(alt.X('ReadYearMonth', axis=alt.Axis(title='Month-Year Read')), alt.Y('count(BookName):Q', axis=alt.Axis(title='No. of Books')),
                                                            color='Category:N',
                                                            tooltip=[alt.Tooltip('Category', title='Category'),
                                                             alt.Tooltip('ReadYearMonth', title='Month'), alt.Tooltip('count(BookName):Q',
                                                              title='Number of Books'),]).configure_view(strokeWidth=0)
st.subheader("Books by Month")
st.altair_chart(fig_books_yearmonth_count, use_container_width=True)
# End Display number of books by monthly buckets

# Begin Display number of books read by author(s)
# Break horizontal layout into two columns
st.subheader("Books by Author(s)")
col1, col2 = st.columns([8, 1])
with col2:
    category = st.selectbox(
     'Category',
     ('All', 'Biography/Autobiography', 'Fantasy', 'Historical Fiction', 'Informational', 
     'Mystery', 'Realistic Fiction', 'Poetry', 'Traditional Literature'
     ))
if category == 'All':
    df_categories = df
else:
    df_categories = df[df['Category'] == category] 
fig_author_count = alt.Chart(df_categories).mark_bar().encode(alt.X('Authors:N', sort='-y'), 
                                                            alt.Y('count(BookName):Q', axis=alt.Axis(title='No. of Books')),
                                                            tooltip=['Authors', alt.Tooltip('count(BookName)',
                                                             title='Number of Books')]).configure_view(strokeWidth=0).interactive()
with col1:
    st.altair_chart(fig_author_count, use_container_width=True)
# End Display number of books read by author(s)..

# Begin Display all books in a dataframe with selected columns
st.subheader("All the books!")
st.caption('Select a row to see it\'s image')
col1, col2 = st.columns([8, 1])
gb = GridOptionsBuilder.from_dataframe(df[['BookName', 'Authors', 'Rating', 'Category', 'ReadYearMonth', 'Thumbnail']])
gb.configure_column('Thumbnail', hide=True) 
gb.configure_pagination()
gb.configure_side_bar(columns_panel = False)
gb.configure_selection(selection_mode="single", use_checkbox=True)
# gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc="count", editable=True)
gridOptions = gb.build()

with col1:data = AgGrid(df[['BookName', 'Authors', 'Rating', 'Category', 'ReadYearMonth', 'Thumbnail']].sort_values(by='ReadYearMonth', ascending=False),
 gridOptions=gridOptions, enable_enterprise_modules=True, fit_columns_on_grid_load=True, theme='streamlit', update_mode=GridUpdateMode.SELECTION_CHANGED)

# Display book thumbnail
with col2:
    if data['selected_rows']:
        if data['selected_rows'][0]['Thumbnail']!= 'None':
            st.image(data['selected_rows'][0]['Thumbnail'])
# End Display all books in a dataframe with selected columns
