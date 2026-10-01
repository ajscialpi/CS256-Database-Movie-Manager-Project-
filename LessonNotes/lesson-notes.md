## Build the page structure with HTML
9/16/26

The <!doctype html> line tells the browser to use modern HTML. The html element has lang="en" to identify the document language. Inside head, title supplies the browser-tab text and the stylesheet link loads ../templates/brand.css. The viewport setting helps the page use the available screen width on a phone.

A link takes the user somewhere. A button performs an action, such as submitting a form. Give either one words that explain the result: “View report” is more useful than “Click here.” A div is a general container for grouping content. It does not describe a user action or a document section by itself.

A table is useful for records that readers compare by column. A caption says what the table contains. A th cell identifies a heading and a td cell contains an ordinary value. scope="col" marks a column heading; scope="row" marks the label that identifies one row. The code example in this section is a sample table for your mockup. Activity 3 adapts its headings and sample values to your project.

## Connecting Flask to front end
9/30/26

browser GET / → app.py: home → templates/index.html → HTML response

- browser GET / → app.py: home:
  The browser requests the homepage (/), which causes Flask to run the home() function in app.py.

- app.py: home → templates/index.html:
  The home() function uses render_template() to load index.html and pass the rows data to the template.

- templates/index.html → HTML response:
  Jinja processes the template and loops through the rows. The completed HTML is then returned to the browser.