import { zipSync } from "fflate";

type DbfField = [name: string, kind: "C" | "N" | "D", width: number, decimals: number];

function dbf(fields: DbfField[], records: Record<string, string>[]): Uint8Array {
  const headerLength = 32 + fields.length * 32 + 1;
  const recordLength = 1 + fields.reduce((total, field) => total + field[2], 0);
  const output = new Uint8Array(headerLength + recordLength * records.length + 1);
  const view = new DataView(output.buffer);
  output[0] = 3;
  output.set([126, 8, 10], 1);
  view.setUint32(4, records.length, true);
  view.setUint16(8, headerLength, true);
  view.setUint16(10, recordLength, true);
  for (const [index, [name, kind, width, decimals]] of fields.entries()) {
    const start = 32 + index * 32;
    for (const [offset, character] of [...name.slice(0, 10)].entries()) {
      output[start + offset] = character.charCodeAt(0);
    }
    output[start + 11] = kind.charCodeAt(0);
    output[start + 16] = width;
    output[start + 17] = decimals;
  }
  output[headerLength - 1] = 13;
  for (const [recordIndex, record] of records.entries()) {
    let cursor = headerLength + recordIndex * recordLength;
    output[cursor] = 32;
    cursor += 1;
    for (const [name, kind, width] of fields) {
      const raw = kind === "D" ? (record[name] ?? "").replaceAll("-", "") : (record[name] ?? "");
      const value = (kind === "N" ? raw.padStart(width) : raw.padEnd(width)).slice(0, width);
      for (let offset = 0; offset < width; offset += 1) output[cursor + offset] = value.charCodeAt(offset);
      cursor += width;
    }
  }
  output[output.length - 1] = 26;
  return output;
}

export function migrationArchive(options: { unbalanced?: boolean } = {}): Uint8Array {
  const accountFields: DbfField[] = [
    ["A_ACC_CODE", "C", 10, 0], ["DESC", "C", 40, 0], ["ACC_TYPE", "C", 1, 0],
    ["OPEN_BAL", "N", 17, 3], ["CURR_BAL", "N", 17, 3], ["BAL_1", "N", 17, 3],
    ["BUG_1", "N", 17, 3], ["CURR", "C", 5, 0],
  ];
  const mainFields: DbfField[] = [
    ["M_ACC_CODE", "C", 10, 0], ["M_PERIOD", "N", 2, 0], ["M_DATE", "D", 8, 0],
    ["M_TRANS_DE", "C", 40, 0], ["M_REF", "C", 10, 0], ["M_DEBIT", "N", 17, 3],
    ["M_CREDIT", "N", 17, 3], ["M_GNAME", "C", 10, 0], ["M_CURR", "C", 5, 0],
    ["M_EXRATE", "N", 14, 7], ["M_CREDITX", "N", 17, 3], ["M_DEBITX", "N", 17, 3],
    ["KEY", "C", 10, 0], ["RECNO", "N", 10, 0],
  ];
  const credit = options.unbalanced ? "124.550" : "125.550";
  return zipSync({
    "GLACCNT.DAT": dbf(accountFields, [
      { A_ACC_CODE: "1000", DESC: "Cash", ACC_TYPE: "B", OPEN_BAL: "0", CURR_BAL: "125.550", BAL_1: "125.550", BUG_1: "120", CURR: "SGD" },
      { A_ACC_CODE: "4000", DESC: "Sales", ACC_TYPE: "I", OPEN_BAL: "0", CURR_BAL: "-125.550", BAL_1: "-125.550", BUG_1: "-100", CURR: "SGD" },
    ]),
    "GLMAIN.DAT": dbf(mainFields, [
      { M_ACC_CODE: "1000", M_PERIOD: "1", M_DATE: "2027-06-01", M_TRANS_DE: "Browser migration", M_REF: "MIG-1", M_DEBIT: "125.550", M_CREDIT: "0", M_GNAME: "MIGRATION", M_CURR: "SGD", M_EXRATE: "1", M_CREDITX: "0", M_DEBITX: "125.550", KEY: "WEB0001", RECNO: "1" },
      { M_ACC_CODE: "4000", M_PERIOD: "1", M_DATE: "2027-06-01", M_TRANS_DE: "Browser migration", M_REF: "MIG-1", M_DEBIT: "0", M_CREDIT: credit, M_GNAME: "MIGRATION", M_CURR: "SGD", M_EXRATE: "1", M_CREDITX: credit, M_DEBITX: "0", KEY: "WEB0001", RECNO: "2" },
    ]),
  });
}
