import { bagsForDose, doseForBags, nitrogenGrams, toTenths } from "./bags";
import { maskNationalId, parseDose, validateForm } from "./validation";

const URE = { ley_principal: 46, ley_n: 46, kg_bulto: 50 };
const DAP = { ley_principal: 46, ley_n: 18, kg_bulto: 50 };
const KCL = { ley_principal: 60, ley_n: 0, kg_bulto: 50 };

describe("bags (must match the server's integer arithmetic)", () => {
  it.each([
    ["OF-1187 S-104 URE 80", 80.0, 42.5, URE, 148],
    ["OF-1190 S-117 DAP 46", 46.0, 35.2, DAP, 70],
    ["OF-1191 S-117 URE 40", 40.0, 35.2, URE, 61],
    ["OF-1195 S-212 URE 43.7", 43.7, 27.4, URE, 52],
    ["OF-1196 S-208 KCL 120", 120.0, 48.6, KCL, 194],
    ["OF-1198 S-221 URE 30", 30.0, 16.0, URE, 21],
  ])("%s", (_n, dose, area, product, expected) => {
    expect(bagsForDose(toTenths(dose), toTenths(area), product)).toBe(expected);
  });

  it("computes exact nitrogen grams", () => expect(nitrogenGrams(148, URE)).toBe(3_404_000));

  it("finds the dose that yields a given bag count, or null", () => {
    const d = doseForBags(52, toTenths(35.2), URE)!;
    expect(bagsForDose(d, toTenths(35.2), URE)).toBe(52);
    expect(doseForBags(0, 352, URE)).toBeNull();
  });
});

describe("dose parsing", () => {
  it.each([["80", 800], ["80.0", 800], ["43,7", 437], ["0.1", 1], ["200", 2000], [" 12.5 ", 125]])("accepts %s", (text, tenths) => {
    expect(parseDose(text)).toMatchObject({ ok: true, tenths });
  });
  it.each([["", "dose_number"], ["abc", "dose_number"], ["0", "dose_range"], ["200.1", "dose_range"], ["-5", "dose_number"], ["80.05", "dose_decimals"]])("rejects %j", (text, code) => {
    expect(parseDose(text)).toMatchObject({ ok: false, issue: { code } });
  });
});

describe("form validation", () => {
  const ok = { order: "OF-2026-1187", product: "URE", dose: "80.0", nationalId: "1113654321" };
  it("accepts a valid form", () => expect(validateForm(ok)).toEqual({}));
  it("reports every wrong field with the API's field names", () => {
    const e = validateForm({ order: "x", product: "", dose: "0", nationalId: "123" });
    expect(Object.keys(e).sort()).toEqual(["cedula_capataz", "dosis_kg_ha", "orden", "producto"]);
  });
  it("id accepts 6 to 10 digits only", () => {
    expect(validateForm({ ...ok, nationalId: "123456" })).toEqual({});
    expect(validateForm({ ...ok, nationalId: "12345" }).cedula_capataz).toBeDefined();
    expect(validateForm({ ...ok, nationalId: "12345678901" }).cedula_capataz).toBeDefined();
  });
  it("masks the national id leaving 4 digits", () => expect(maskNationalId("1113654321")).toBe("xxxxxx4321"));
});
