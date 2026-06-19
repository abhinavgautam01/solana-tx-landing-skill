import {
  ComputeBudgetProgram,
  TransactionMessage,
  VersionedTransaction,
} from "@solana/web3.js";

export async function pay(connection: any, wallet: any, appInstruction: any) {
  const latest = await connection.getLatestBlockhash("confirmed");
  const instructions = [
    ComputeBudgetProgram.setComputeUnitLimit({ units: 250_000 }),
    ComputeBudgetProgram.setComputeUnitPrice({ microLamports: 10_000 }),
    appInstruction,
  ];
  const message = new TransactionMessage({
    payerKey: wallet.publicKey,
    recentBlockhash: latest.blockhash,
    instructions,
  }).compileToV0Message();

  const tx = new VersionedTransaction(message);
  const signed = await wallet.signTransaction(tx);
  const signature = await connection.sendRawTransaction(signed.serialize(), {
    skipPreflight: false,
    preflightCommitment: "confirmed",
  });

  return connection.confirmTransaction(
    {
      signature,
      blockhash: latest.blockhash,
      lastValidBlockHeight: latest.lastValidBlockHeight,
    },
    "confirmed",
  );
}

