import { manageDatabase } from "./database-control.mjs";

export default function globalSetup() {
  manageDatabase("prepare");
}
