# Server logic — Server.* objects, cloud flows, and Liquid invocation

Shared reference for Power Pages **server logic** (server-side JavaScript on the portal runtime).
Used by `pp-serverlogic` and `pp-liquid`.

> **Authority:** Microsoft Learn. **Sources:** [Server objects](https://learn.microsoft.com/en-us/power-pages/configure/server-objects) ·
> [Author server logic](https://learn.microsoft.com/en-us/power-pages/configure/author-server-logic) ·
> blogs: [Extend server logic with cloud flows](https://www.microsoft.com/en-us/power-platform/blog/power-pages/extend-server-logic-with-power-automate-cloud-flows-in-power-pages/) ·
> [Extend Liquid with server logic](https://www.microsoft.com/en-us/power-platform/blog/power-pages/extend-liquid-with-server-logic-in-power-pages/).

A **server logic** record holds server-side JS functions. Create it in the design studio **Set up →
Server logic**, assign it a **web role**, and edit the code in VS Code. It can be invoked from a
client script (over HTTP) or from Liquid during page render.

## The `Server.*` objects

| Object | What it does |
|---|---|
| `Server.Connector.HttpClient` | Call external services: `GetAsync(url, headers)`, `PostAsync(url, body, headers, contentType)`, `PutAsync`, `PatchAsync`, `DeleteAsync`. Body content types: `application/json`, `text/html`, `application/x-www-form-urlencoded` only. |
| `Server.Connector.Dataverse` | CRUD + custom APIs: `CreateRecord(entitySetName, payload)`, `RetrieveRecord(...)`, `RetrieveMultipleRecords(entitySetName, options[, skipCache])`, `UpdateRecord(...)`, `DeleteRecord(...)`, `InvokeCustomApi(method, url[, payload])`. **Use the EntitySetName** (e.g. `accounts`). |
| `Server.Connector.CloudFlow` | **Trigger a Power Automate cloud flow** — `TriggerAsync(flowId, payload)` (see below). |
| `Server.SiteSetting` | `Get("Search/Enabled")` — read a site setting. |
| `Server.EnvironmentVariable` | `get("SITEPATH")` — read an environment variable. |
| `Server.Website` | Current website record, e.g. `Server.Website.adx_primarydomain`. |
| `Server.User` | Signed-in user, e.g. `Server.User.fullname`. **`null` if anonymous.** |
| `Server.Logger` | `Log(...)`, `Warn(...)`, `Error(...)` — diagnostics viewable in the DevTools extension. |
| `Server.Context` | Invocation context (see below). |

Async connector calls return a response envelope: `{ StatusCode, Body, IsSuccessStatusCode,
ReasonPhrase, ServerError, ServerErrorMessage, Headers }`. Mark calling functions `async` and `await`.

> 🔐 **Never store secrets (API keys, credentials) in server-logic code.** Keep them in Azure Key
> Vault, surface them through environment variables, and reference them via site settings.

## Trigger a Power Automate cloud flow

`Server.Connector.CloudFlow.TriggerAsync(flowId, payload)` is the server-side equivalent of the
`/_api/cloudflow/v1.0/trigger/<guid>` endpoint.

```javascript
async function post() {
  const flowId  = "00000000-0000-0000-0000-000000000001";  // from Set up > Integrations > Cloud flows
  const payload = JSON.stringify({ Location: "Seattle" });   // keyed by the flow trigger's params

  const response = JSON.parse(await Server.Connector.CloudFlow.TriggerAsync(flowId, payload));
  if (!response.IsSuccessStatusCode) {
    Server.Logger.Error("Cloud flow failed: " + response.ReasonPhrase);
    return JSON.stringify({ success: false, error: response.ReasonPhrase });
  }
  return JSON.stringify({ success: true, flowResponse: response.Body });
}
```

Prerequisites: **create the flow and add it to the site with an authorized web role**; the signed-in
user must hold one of those roles. `siteId`, `siteUrl`, and `userId` are added to the payload
automatically. If the flow has no response action it returns `202 Accepted` with an empty body
(reported as `IsSuccessStatusCode: true`). **ALM:** register the flow in the target environment
before invoking it there.

## Two ways to invoke server logic

**1. From a client script** — HTTP to `/_api/serverlogics/<name>` with a CSRF token (`safeAjax`):

```javascript
shell.safeAjax({
  type: "POST",
  url: "/_api/serverlogics/customer-summary",
  contentType: "application/json",
  data: JSON.stringify({ name: "Sample" }),
  success: function (res) { console.log(res); }
});
```

Response: `{ RequestId, Success, Data, ExecutionTime, ServerLogicName, Error }`.

**2. From Liquid** (server-side render — **no CSRF, no client request**):

```liquid
{% assign inputData = '{"category":"active","maximumResults":5}' %}
{% serverlogic name: 'customer-summary', operation: 'getSummary', input: inputData, output: result %}
{% if result.success %}
  <p>{{ result.data.category | escape }}</p>
{% else %}
  <p>Summary unavailable.</p>
{% endif %}
```

The function reads the input via `Server.Context.Input`:

```javascript
function getSummary() {
  const input = JSON.parse(Server.Context.Input || "{}");
  return JSON.stringify({ category: input.category, maximumResults: input.maximumResults });
}
```

Assign the server logic record to a web role the current user can access. **Validate input** before
using it in Dataverse or external calls. Liquid invocation runs **during page render**, so
long-running Dataverse/HTTP calls increase page response time — keep them light.

`Server.Context` properties: `ActivityId`, `FunctionName`, `ServerLogicName` (HTTP + Liquid);
`Body`, `Headers`, `HttpMethod`, `QueryParameters`, `Url` (HTTP); `Input` (Liquid).

## Limitations (authoritative — the sandbox is documented, not guesswork)

Server logic runs on the server: **no browser APIs** (`fetch`, `XMLHttpRequest`, DOM). The runtime
**rejects** scripts containing these patterns (dynamic execution / process control / prototype
manipulation):

```
__dirname   __filename   import(   import from   eval(   Function(
setTimeout(   setInterval(   setImmediate(   process.exit   process.kill   child_process
fs.   require(   constructor.constructor   this.constructor   arguments.callee
with(   delete   Object.getPrototypeOf   Object.setPrototypeOf   Proxy(   Reflect.
Symbol.for   __proto__   prototype   debugger
```

> *(This supersedes the community observation that server logic has "hidden" constraints — Microsoft
> now publishes the exact list above. — Tino Rabe flagged the behavior; the list is authoritative.)*
