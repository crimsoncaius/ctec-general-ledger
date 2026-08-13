import { manageDatabase } from "./database-control.mjs";

export default function globalTeardown() {
  manageDatabase("drop");
}
