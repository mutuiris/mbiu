const apiUrl = process.env.NEXT_PUBLIC_API_URL;
if (!apiUrl) throw new Error("NEXT_PUBLIC_API_URL is not set. Add it to the repo's .env file.");

/** Base URL of the Mbiu API, without a trailing slash. */
export const API_URL = apiUrl.replace(/\/$/, "");
