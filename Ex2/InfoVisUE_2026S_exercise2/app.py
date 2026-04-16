from flask import Flask, render_template
import json

import pandas as pd

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)

# ensure that we can reload when we change the HTML / JS for debugging
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

COUNTRIES = ['Afghanistan', 'Albania', 'Algeria', 'Angola', 'Argentina', 'Armenia', 'Australia', 'Austria', 'Azerbaijan', 
             'Brazil', 'Bulgaria', 
             'Cameroon', 'Chile', 'China', 'Colombia', 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic', 
             'Ecuador', 'Egypt, Arab Rep.', 'Eritrea', 'Ethiopia', 'France', 
             'Germany', 'Ghana', 'Greece', 
             'India', 'Indonesia', 'Iran, Islamic Rep.', 'Iraq', 'Ireland', 'Italy', 
             'Japan', 'Jordan', 
             'Kazakhstan', 'Kenya', 
             'Lebanon', 
             'Malta', 'Mexico', 'Morocco', 
             'Pakistan', 'Peru', 'Philippines', 
             'Russian Federation', 
             'Syrian Arab Republic', 
             'Tunisia', 'Turkey', 
             'Ukraine']

@app.route('/')
def data():
    df = pd.read_csv("data/agriRuralDevelopment_cleaned.csv")
    df = df.rename(columns={'Country Name': 'country_name', 'Country Code': 'country_code'})
    df_filtered = df[df['country_name'].isin(COUNTRIES)]

    features = [col for col in df.columns if col not in ['country_name', 'country_code', 'year']]
    df_2020 = df_filtered[df_filtered['year'] == 2020].dropna(subset=features)

    x = StandardScaler().fit_transform(df_2020[features])
    pca = PCA(n_components=2)
    principalComponents = pca.fit_transform(x)

    pca_data = []
    for i, country in enumerate(df_2020['country_name'].tolist()):
        pca_data.append({
            'country_name': country,
            'x': principalComponents[i, 0],
            'y': principalComponents[i, 1]
        })

    # Prepare full data for the time series
    full_data = df_filtered.to_dict(orient='records')

    # return the index file and the data
    return render_template("index.html", 
                           pca_results=json.dumps(pca_data),
                           full_data=json.dumps(full_data))


if __name__ == '__main__':
    print("Starting the Flask server...")
    app.run()
