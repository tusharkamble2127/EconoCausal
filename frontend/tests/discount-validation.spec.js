
import { test, expect } from "@playwright/test";

test.describe("Discount level validation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:5173");
  });

  test("shows an error for an empty discount", async ({ page }) => {
    await page.getByRole("button", { name: "Add" }).click();

    await expect(
      page.getByRole("alert")
    ).toHaveText("Please enter a discount percentage.");
  });

  test("rejects a discount above 100%", async ({ page }) => {
    const input = page.getByRole("spinbutton", {
      name: "Discount percentage",
    });

    await input.fill("101");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.getByRole("alert")).toHaveText(
      "Discount must be between 0% and 100%."
    );
  });

  test("rejects a duplicate discount", async ({ page }) => {
    const input = page.getByRole("spinbutton", {
      name: "Discount percentage",
    });

    await input.fill("5");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.getByRole("alert")).toHaveText(
      "5% already exists."
    );
  });

  test("adds a valid discount", async ({ page }) => {
    const input = page.getByRole("spinbutton", {
      name: "Discount percentage",
    });

    await input.fill("12.5");
    await page.getByRole("button", { name: "Add" }).click();

    await expect(
      page.getByText("12.5%", { exact: true })
    ).toBeVisible();

    await expect(page.getByRole("alert")).toHaveCount(0);
  });

  test("does not offer a remove button for the 0% control", async ({
    page,
  }) => {
    await expect(
      page.getByRole("button", { name: "Remove 0% discount level" })
    ).toHaveCount(0);

    await expect(
      page.getByText("0% is the control (no-discount) arm and cannot be removed.")
    ).toBeVisible();
  });
});
