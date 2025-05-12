// shared/src/utils/__tests__/dateUtils.test.ts
import { describe, it, expect } from "vitest";
import {
  formatDateOnly,
  formatTimeOnly,
  formatOffDates,
} from "./dateUtils";

describe("formatDateOnly", () => {
  // it("formats valid date string to MM/DD/YY", () => {
  //   expect(formatDateOnly("2024-12-01")).toBe("12/1/24");
  //   expect(formatDateOnly("2024-12-01T14:45:00")).toBe("12/1/24");
  //   expect(formatDateOnly("5/5/25")).toBe("5/5/25");
  // });

  it("formats valid Date object to M/d/yy", () => {
    expect(formatDateOnly(new Date("2024-12-01T06:00:00.000Z"))).toBe("12/1/24");
  });

  // it("returns empty string for undefined", () => {
  //   expect(formatDateOnly(undefined as any)).toBe("");
  // });

  // it("throws error on invalid input type", () => {
  //   expect(() => formatDateOnly(123 as any)).toThrow("Invalid date input");
  //   expect(() => formatDateOnly({} as any)).toThrow("Invalid date input");
  // });
});

describe("formatTimeOnly", () => {
  // it("formats valid date string to h:mm AM/PM", () => {
  //   expect(formatTimeOnly("2024-12-01T13:45:00")).toMatch(/1:45 PM|1:45 PM/);
  // });

  it("formats valid Date object", () => {
    expect(formatTimeOnly(new Date("2024-06-01T07:30:00Z"))).toMatch(/3:30 AM|3:30 AM/);
    expect(formatTimeOnly(new Date("2024-12-01T07:30:00.000Z"))).toMatch(/2:30 AM|2:30 AM/);
  });

  // it("throws error on invalid input type", () => {
  //   expect(() => formatTimeOnly(123 as any)).toThrow("Invalid date input");
  //   expect(() => formatTimeOnly({} as any)).toThrow("Invalid date input");
	// expect(() => formatTimeOnly(undefined as any)).toThrow("Invalid date input");
  // });
});

describe("formatOffDates", () => {
  // it("formats single date string", () => {
  //   expect(formatOffDates("2024-12-01")).toBe("12/1/24");
  // });

  it("formats comma-separated date strings", () => {
    // expect(formatOffDates("2024-12-01, 2024-12-25")).toBe("12/1/24, 12/25/24");
    expect(formatOffDates("12/1/24, 12/25/24")).toBe("12/1/24, 12/25/24");
  });

  it("formats Date object", () => {
    expect(formatOffDates(new Date("2024-12-01T12:00:00.000Z"))).toBe("12/1/24");
  });

  // it("returns empty string for undefined", () => {
  //   expect(formatOffDates(undefined)).toBe("");
  // });

  // it("throws error on invalid type", () => {
  //   expect(() => formatOffDates(42 as any)).toThrow("Invalid date input");
  //   expect(() => formatOffDates({} as any)).toThrow("Invalid date input");
  // });
});