import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { balance, mockFetch, renderApp, TOKEN } from "./test/helpers";

/** Paste the test token and press *Enter*. */
async function signIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Token de sesión"), TOKEN);
  await user.click(screen.getByRole("button", { name: "Entrar" }));
}
/** Sign in and look up S-117, waiting for its balance to appear. */
async function openPlot(user: ReturnType<typeof userEvent.setup>) {
  await signIn(user);
  await user.type(screen.getByLabelText(/Código de la suerte/), "S-117");
  await user.click(screen.getByRole("button", { name: "Consultar balance" }));
  await screen.findByRole("heading", { name: /Balance de nitrógeno de S-117/ });
}
/** Fill the dispatch form for OF-2026-1191 (URE) with the given dose and a foreman id. */
async function fillForm(user: ReturnType<typeof userEvent.setup>, dose = "40.0") {
  await user.type(screen.getByLabelText("Orden de fertilización"), "OF-2026-1191");
  await user.selectOptions(screen.getByLabelText("Producto"), "URE");
  await user.type(screen.getByLabelText(/^Dosis/), dose);
  await user.type(screen.getByLabelText("Cédula del capataz"), "94387120");
}

/** A 409 `LIMITE_NITROGENO` body: 52 bags fit and 34.43 kg N/ha remain. */
const limit409 = {
  motivo: "LIMITE_NITROGENO", mensaje: "x", n_despacho_kg_ha: 39.86, bultos_maximos: 52,
  balance: balance({ n_ciclo_kg_ha: 125.57, n_disponible_kg_ha: 34.43 }),
};

describe("ventanilla", () => {
  it("shows the balance with the history and only masked foreman ids", async () => {
    mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp();
    await openPlot(user);
    expect(screen.getByText("52,32 kg N/ha")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    expect(within(table).getByText("xxxxxx4321")).toBeInTheDocument();
    expect(screen.getByText("Bodega NORTE · Ventanilla NORTE-1")).toBeInTheDocument();
  });

  it("asks for confirmation with the bag count, then registers and wipes the national id", async () => {
    const calls = mockFetch((_url, init) => init?.method === "POST"
      ? { status: 201, body: { id: "9", orden: "OF-2026-1191", suerte: "S-117", producto: "URE", bultos: 61 } }
      : { status: 200, body: balance() });
    const user = userEvent.setup();
    renderApp();
    await openPlot(user);
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Revisar despacho" }));

    const review = await screen.findByRole("group", { name: "Confirmación en ventanilla" });
    expect(within(review).getByText("61")).toBeInTheDocument();            // bags read aloud
    expect(within(review).getByText("xxxxxx7120")).toBeInTheDocument();     // never the full id
    expect(screen.queryByText("94387120")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.init?.method === "POST")).toHaveLength(0); // nothing sent before confirming

    await user.click(screen.getByRole("button", { name: "Confirmar y registrar" }));
    expect(await screen.findByText("Despacho registrado")).toBeInTheDocument();
    const post = calls.find((c) => c.init?.method === "POST")!;
    expect(JSON.parse(post.init!.body as string)).toEqual({
      orden: "OF-2026-1191", producto: "URE", dosis_kg_ha: 40, cedula_capataz: "94387120", bultos_confirmados: 61,
    });
    expect(screen.getByLabelText("Cédula del capataz")).toHaveValue("");
    expect(screen.getByLabelText("Orden de fertilización")).toHaveValue("");
  });

  it("on 409 keeps every field, shows available N and max bags, and lets the user adjust the dose", async () => {
    mockFetch((_u, init) => init?.method === "POST" ? { status: 409, body: limit409 } : { status: 200, body: balance() });
    const user = userEvent.setup();
    renderApp();
    await openPlot(user);
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Revisar despacho" }));
    await user.click(await screen.findByRole("button", { name: "Confirmar y registrar" }));

    expect(await screen.findByText("El despacho supera el límite de nitrógeno")).toBeInTheDocument();
    expect(screen.getByText(/Caben como máximo 52 bultos de URE/)).toBeInTheDocument();
    expect(screen.getByText(/Disponible: 34,43 kg N\/ha/)).toBeInTheDocument();
    expect(screen.getByLabelText("Orden de fertilización")).toHaveValue("OF-2026-1191");
    expect(screen.getByLabelText("Cédula del capataz")).toHaveValue("94387120");

    await user.click(screen.getByRole("button", { name: /Usar 52 bultos/ }));
    expect(screen.getByLabelText(/^Dosis/)).toHaveValue("34.0")   // 34.0 kg/ha -> exactly 52 bags;
    expect(screen.getByLabelText(/^Dosis/)).toHaveFocus();
  });

  it("lists every wrong field in a summary and links to it", async () => {
    mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp();
    await openPlot(user);
    await user.click(screen.getByRole("button", { name: "Revisar despacho" }));
    const summary = await screen.findByText("Corrija 4 campo(s) antes de continuar");
    expect(summary.closest("[role=alert]")).toHaveFocus();
    expect(screen.getByLabelText("Orden de fertilización")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Orden de fertilización")).toHaveAccessibleDescription(/OF-AAAA-NNNN/);
  });

  it("maps server field errors to their inputs (duplicate order)", async () => {
    mockFetch((_u, init) => init?.method === "POST"
      ? { status: 409, body: { motivo: "ORDEN_DUPLICADA", mensaje: "Esa orden de fertilización ya fue despachada." } }
      : { status: 200, body: balance() });
    const user = userEvent.setup();
    renderApp();
    await openPlot(user);
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Revisar despacho" }));
    await user.click(await screen.findByRole("button", { name: "Confirmar y registrar" }));
    await waitFor(() => expect(screen.getByLabelText("Orden de fertilización")).toHaveAttribute("aria-invalid", "true"));
    expect(screen.getAllByText(/ya fue despachada/).length).toBeGreaterThan(0);
  });

  it("the scanner's Enter in the id field opens the review, it does not register", async () => {
    const calls = mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp();
    await openPlot(user);
    await fillForm(user);
    await user.type(screen.getByLabelText("Cédula del capataz"), "{Enter}");
    expect(await screen.findByRole("group", { name: "Confirmación en ventanilla" })).toBeInTheDocument();
    expect(calls.filter((c) => c.init?.method === "POST")).toHaveLength(0);
  });

  it("masks the national id input and never stores anything in the browser", async () => {
    mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp();
    await openPlot(user);
    await fillForm(user);
    expect(screen.getByLabelText("Cédula del capataz")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Cédula del capataz")).toHaveAttribute("autocomplete", "off");
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(document.cookie).toBe("");
  });

  it("shows plot errors for 403 and 404", async () => {
    let status = 404;
    mockFetch(() => ({ status, body: {} }));
    const user = userEvent.setup();
    renderApp();
    await signIn(user);
    await user.type(screen.getByLabelText(/Código de la suerte/), "S-999");
    await user.click(screen.getByRole("button", { name: "Consultar balance" }));
    expect(await screen.findByText("La suerte no existe.")).toBeInTheDocument();
    status = 403;
    await user.click(screen.getByRole("button", { name: "Consultar balance" }));
    expect(await screen.findByText(/no pertenece a la bodega/)).toBeInTheDocument();
  });

  it("rejects a malformed plot code without calling the server", async () => {
    const calls = mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp();
    await signIn(user);
    await user.type(screen.getByLabelText(/Código de la suerte/), "104");
    await user.click(screen.getByRole("button", { name: "Consultar balance" }));
    expect(await screen.findByText(/Use el formato S-NNN/)).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("closes the session and wipes the screen after inactivity", async () => {
    mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp("es", 150);
    await signIn(user);
    expect(await screen.findByText("La sesión se cerró por inactividad.", {}, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.getByLabelText("Token de sesión")).toHaveValue("");
  });

  it("an expired token (401) sends the user back to sign in", async () => {
    mockFetch(() => ({ status: 401, body: {} }));
    const user = userEvent.setup();
    renderApp();
    await signIn(user);
    await user.type(screen.getByLabelText(/Código de la suerte/), "S-117");
    await user.click(screen.getByRole("button", { name: "Consultar balance" }));
    expect(await screen.findByText("Su sesión terminó. Vuelva a ingresar.")).toBeInTheDocument();
  });

  it("rejects a token that is not a session token", async () => {
    renderApp();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Token de sesión"), "basura");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(screen.getByText("El token no es válido.")).toBeInTheDocument();
  });

  it("switches the whole UI to English", async () => {
    mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp();
    await user.click(screen.getByRole("button", { name: "Cambiar idioma a inglés" }));
    expect(screen.getByRole("heading", { name: "Dispatch counter" })).toBeInTheDocument();
    expect(screen.getByLabelText("Session token")).toBeInTheDocument();
  });

  it("sends the UI language to the server so its messages match", async () => {
    const calls = mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    renderApp("en");
    await user.type(screen.getByLabelText("Session token"), TOKEN);
    await user.click(screen.getByRole("button", { name: "Enter" }));
    await user.type(screen.getByLabelText(/Plot code/), "S-117");
    await user.click(screen.getByRole("button", { name: "Look up balance" }));
    await screen.findByRole("heading", { name: /Nitrogen balance of S-117/ });
    expect((calls[0].init!.headers as Record<string, string>)["Accept-Language"]).toBe("en");
    expect((calls[0].init!.headers as Record<string, string>).Authorization).toBe(`Bearer ${TOKEN}`);
  });
});

describe("accessibility (axe, WCAG 2.2 A/AA rules)", () => {
  const run = (container: HTMLElement) => axe(container, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"] } });

  it("sign-in screen", async () => {
    const { container } = renderApp();
    expect(await run(container)).toHaveNoViolations();
  });

  it("balance, history and form", async () => {
    mockFetch(() => ({ status: 200, body: balance() }));
    const user = userEvent.setup();
    const { container } = renderApp();
    await openPlot(user);
    expect(await run(container)).toHaveNoViolations();
  });

  it("form with errors, the review step and the limit notice", async () => {
    mockFetch((_u, init) => init?.method === "POST" ? { status: 409, body: limit409 } : { status: 200, body: balance() });
    const user = userEvent.setup();
    const { container } = renderApp();
    await openPlot(user);
    await user.click(screen.getByRole("button", { name: "Revisar despacho" }));
    expect(await run(container)).toHaveNoViolations();
    await fillForm(user);
    await user.click(screen.getByRole("button", { name: "Revisar despacho" }));
    await screen.findByRole("group", { name: "Confirmación en ventanilla" });
    expect(await run(container)).toHaveNoViolations();
    await user.click(screen.getByRole("button", { name: "Confirmar y registrar" }));
    await screen.findByText("El despacho supera el límite de nitrógeno");
    expect(await run(container)).toHaveNoViolations();
  });

  it("English version", async () => {
    mockFetch(() => ({ status: 200, body: balance() }));
    const { container } = renderApp("en");
    expect(await run(container)).toHaveNoViolations();
  });
});
