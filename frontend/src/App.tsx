import { FluentProvider, webDarkTheme, webLightTheme } from "@fluentui/react-components";
import { lazy, Suspense } from "react";
import { Redirect, Route, Switch } from "react-router-dom";

import { PreferencesProvider, usePreferences } from "./app/preferences";
import { AppShell } from "./components/AppShell";
import { LoadingState } from "./components/QueryState";

const FoundationPage = lazy(() => import("./pages/FoundationPage").then((module) => ({ default: module.FoundationPage })));
const NewAuditPage = lazy(() => import("./pages/NewAuditPage").then((module) => ({ default: module.NewAuditPage })));
const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const PoliciesPage = lazy(() => import("./pages/PoliciesPage").then((module) => ({ default: module.PoliciesPage })));
const PolicyDetailPage = lazy(() => import("./pages/PolicyDetailPage").then((module) => ({ default: module.PolicyDetailPage })));
const FindingsPage = lazy(() => import("./pages/FindingsPage").then((module) => ({ default: module.FindingsPage })));
const FindingDetailPage = lazy(() => import("./pages/FindingDetailPage").then((module) => ({ default: module.FindingDetailPage })));
const ConflictsPage = lazy(() => import("./pages/ConflictsPage").then((module) => ({ default: module.ConflictsPage })));
const KnowledgePacksPage = lazy(() => import("./pages/KnowledgePacksPage").then((module) => ({ default: module.KnowledgePacksPage })));
const ReportsPage = lazy(() => import("./pages/ReportsPage").then((module) => ({ default: module.ReportsPage })));
const TenantPage = lazy(() => import("./pages/SecondaryPages").then((module) => ({ default: module.TenantPage })));
const SettingsPage = lazy(() => import("./pages/SecondaryPages").then((module) => ({ default: module.SettingsPage })));
const HelpPage = lazy(() => import("./pages/SecondaryPages").then((module) => ({ default: module.HelpPage })));
const AboutPage = lazy(() => import("./pages/SecondaryPages").then((module) => ({ default: module.AboutPage })));

function ApplicationRoutes() {
  const { resolvedTheme } = usePreferences();
  return (
    <FluentProvider theme={resolvedTheme === "dark" ? webDarkTheme : webLightTheme}>
      <AppShell>
        <Suspense fallback={<LoadingState />}>
          <Switch>
            <Route exact path="/" component={FoundationPage} />
            <Route exact path="/audit/new" component={NewAuditPage} />
            <Route exact path="/audit/:auditId/dashboard" component={DashboardPage} />
            <Route exact path="/audit/:auditId/policies" component={PoliciesPage} />
            <Route exact path="/audit/:auditId/policies/:policyId" component={PolicyDetailPage} />
            <Route exact path="/audit/:auditId/findings" component={FindingsPage} />
            <Route exact path="/audit/:auditId/findings/:findingId" component={FindingDetailPage} />
            <Route exact path="/audit/:auditId/conflicts" component={ConflictsPage} />
            <Route exact path="/audit/:auditId/reports" component={ReportsPage} />
            <Route exact path="/knowledge-packs" component={KnowledgePacksPage} />
            <Route exact path="/tenant" component={TenantPage} />
            <Route exact path="/settings" component={SettingsPage} />
            <Route exact path="/help" component={HelpPage} />
            <Route exact path="/about" component={AboutPage} />
            <Redirect to="/" />
          </Switch>
        </Suspense>
      </AppShell>
    </FluentProvider>
  );
}

export default function App() {
  return (
    <PreferencesProvider>
      <ApplicationRoutes />
    </PreferencesProvider>
  );
}
