import express from "express";
// import { schedulePriceChange } from "../lib/price-scheduler";
import { schedulePriceChange } from '@packages/price-scheduler'

export const router = express.Router();

router.post("/", async (req, res) => {
  try {
    const result = await schedulePriceChange(req.body);
    res.json(result);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});