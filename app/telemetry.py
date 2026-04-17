import json
import logging
import os

from fastapi import FastAPI

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


logger = logging.getLogger(__name__)
_telemetry_configured = False


def _connection_string() -> str:
    return os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "").strip()


def setup_telemetry(app: FastAPI) -> None:
    global _telemetry_configured

    connection_string = _connection_string()
    if not connection_string:
        return

    if not _telemetry_configured:
        configure_azure_monitor(connection_string=connection_string)
        _telemetry_configured = True

    if not getattr(app.state, "otel_fastapi_instrumented", False):
        FastAPIInstrumentor.instrument_app(app, excluded_urls="/health")
        app.state.otel_fastapi_instrumented = True
        logger.info("Application Insights + OpenTelemetry enabled")


def build_browser_telemetry_snippet() -> str:
    connection_string = _connection_string()
    if not connection_string:
        return ""

    connection_string_json = json.dumps(connection_string)
    return f"""
  <script type="text/javascript">
  var appInsights=window.appInsights||function(config){{function r(config){{t[config]=function(){{var i=arguments;t.queue.push(function(){{t[config].apply(t,i)}})}}}}var t={{config:config}},u=document,e=window,o="script",s=u.createElement(o),i,f;for(s.src=config.url||"https://js.monitor.azure.com/scripts/b/ai.3.gbl.min.js",u.getElementsByTagName(o)[0].parentNode.appendChild(s),t.cookie=u.cookie,t.queue=[],i=["trackEvent","trackPageView","trackException","trackTrace","trackDependencyData","trackMetric","trackPageViewPerformance","startTrackPage","stopTrackPage","startTrackEvent","stopTrackEvent","addTelemetryInitializer","setAuthenticatedUserContext","clearAuthenticatedUserContext","flush"],f=0;f<i.length;f++)r(i[f]);return t}}({{
    connectionString: {connection_string_json}
  }});
  window.appInsights=appInsights;
  appInsights.trackPageView();
  </script>
"""
