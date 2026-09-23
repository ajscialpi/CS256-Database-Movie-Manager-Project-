// Optional lesson: run these functions in DevTools on YOUR LOCAL S Corp copy.
// First choose an employee under My reports (or switch to Manager view).
// Nothing here changes a record until you explicitly call createReport, editReport, or deleteReport.
const applicationRoot = () => document.querySelector('meta[name="application-root"]').content;
const csrf = () => document.querySelector('meta[name="csrf-token"]').content;
async function api(path, method = 'GET', body) {
  const response = await fetch(applicationRoot() + path, {method,
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf()},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  if (response.status === 204) return null;
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || JSON.stringify(data.errors));
  return data;
}
async function readReports() { return api('/api/incidents'); }
async function createReport(fields) { return api('/api/incidents', 'POST', fields); }
async function editReport(id, fields, version) {
  // PUT needs ALL editable fields and the version returned by the latest GET.
  return api('/api/incidents/' + encodeURIComponent(id), 'PUT', {...fields, version});
}
async function deleteReport(id, version) {
  if (!confirm('Delete this disposable practice report?')) return null;
  return api('/api/incidents/' + encodeURIComponent(id), 'DELETE', {confirm:true, version});
}
// Example safe read: await readReports()
// 409 means your version is stale: GET again, review, and decide what to change.
