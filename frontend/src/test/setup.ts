import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { toHaveNoViolations } from "jest-axe";
import { afterEach, expect } from "vitest";

expect.extend(toHaveNoViolations);
afterEach(() => cleanup());

// axe probes canvas for icon ligatures; jsdom has none (colour contrast is not measurable in jsdom).
HTMLCanvasElement.prototype.getContext = (() => null) as never;
