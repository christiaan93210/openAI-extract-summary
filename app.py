import openai
# import gradio as gr
import textwrap
import os
import re
from time import time, sleep
import fitz  # PyMuPDF
from flask import Flask, render_template, send_file, make_response, url_for, Response, redirect, request, flash, send_from_directory
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = ''
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html',
                           PageTitle="Landing page")

    if __name__ == '__main__':
        app.run(debug=True)

def pdf_to_txt(input_pdf, output_txt):
    # Open the PDF file
    pdf = fitz.open(input_pdf)

    # Initialize an empty string to store the text
    text = "Input: "

    # Iterate through each page in the PDF
    for page_num in range(pdf.page_count):
        # Select the current page
        page = pdf.load_page(page_num)

        # Extract the text from the page
        page_text = page.get_text("text")

        # Add the extracted text to the text string
        text += page_text + "\n"

    # Close the PDF
    pdf.close()

    # Write the extracted text to a text file
    with open(output_txt, "w", encoding="utf-8") as txt_file:
        txt_file.write(text)


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(content, filepath):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def gpt3_completion(prompt, engine='text-davinci-002', temp=0.7, top_p=1.0, tokens=3000, freq_pen=0.0, pres_pen=0.0, stop=['<<END>>']):
    max_retry = 5
    retry = 0
    while True:
        try:
            response = openai.Completion.create(
                engine=engine,
                prompt=prompt,
                temperature=temp,
                max_tokens=tokens,
                top_p=top_p,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                stop=stop
            )
            text = response['choices'][0]['text'].strip()
            text = re.sub('\s+', ' ', text)
            filename = '%s_gpt3.txt' % time()
            with open('gpt3_logs/%s' % filename, 'w') as outfile:
                outfile.write('PROMPT:\n\n' + prompt +
                              '\n\n==============\n\nRESPONSE:\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return 'GPT3 error: %s' % str(oops)
            print('Error Communication with OpenAI:', str(oops))
            sleep(1)

@app.route('/', methods=["POST"])

def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
        openai.api_key = open_file('openaiapikey.txt')
        input_pdf = filename
        output_txt = "input_txt.txt"
        pdf_to_txt(input_pdf, output_txt)
        alltext = open_file('input_txt.txt')
        chunks = textwrap.wrap(alltext, 1000)
        result = list()
        for chunk in chunks:
            prompt = open_file('prompt.txt').replace('<<SUMMARY>>', chunk)
            summary = gpt3_completion(prompt)
            result.append(summary)
            save_file('\n\n'.join(result), 'output.txt')           
            return render_template("result.html", value=''.join(result))
        
@app.route('/uploads/<name>')
def download_file(name):
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

@app.route('/back')
def back():
    return redirect("/")