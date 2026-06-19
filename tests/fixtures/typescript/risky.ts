import {
  Connection,
  Transaction,
} from "@solana/web3.js";

const connection = new Connection("https://api.mainnet-beta.solana.com");

export async function pay(wallet: any, ix: any) {
  const tx = new Transaction();
  tx.add(ix);
  tx.recentBlockhash = (await connection.getLatestBlockhash()).blockhash;
  tx.feePayer = wallet.publicKey;

  const signed = await wallet.signTransaction(tx);
  const signature = await connection.sendRawTransaction(signed.serialize(), {
    skipPreflight: true,
    maxRetries: 0,
  });

  return connection.confirmTransaction(signature);
}

