import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface GradeJobProgress {
  status: "pending" | "running" | "done" | "error";
  processed: number;
  total: number;
  error: string | null;
  failed_images: string[];
}

export async function startGradeJob(
  listOfImages: File[],
  config: File,
  fillThreshold = 0.5,
): Promise<string> {
  const formData = new FormData();

  listOfImages.forEach((image) =>{
    formData.append("list_of_images", image);
  });

  formData.append("config_json", config);
  formData.append("fill_threshold", String(fillThreshold));

  const response = await axios.post(`${API_BASE}/grade/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data.job_id as string;
}

export async function getGradeJobProgress(jobId: string): Promise<GradeJobProgress> {
  const response = await axios.get(`${API_BASE}/grade/${jobId}/progress`);
  return response.data as GradeJobProgress;
}

export async function getGradeJobResult(jobId: string): Promise<Blob> {
  const response = await axios.get(`${API_BASE}/grade/${jobId}/result`, {
    responseType: "blob",
  });
  return response.data as Blob;
}

/** Extracts a user-friendly message from an error thrown by the calls above. */
export async function extractErrorMessage(err: unknown): Promise<string> {
  if (axios.isAxiosError(err)) {
    const data: unknown = err.response?.data;

    if (data instanceof Blob) {
      try {
        const parsed = JSON.parse(await data.text());
        if (parsed && typeof parsed === "object" && "detail" in parsed) {
          return String((parsed as { detail: unknown }).detail);
        }
      } catch {
        // Response body wasn't JSON, fall through to generic handling below.
      }
    } else if (data && typeof data === "object" && "detail" in data) {
      return String((data as { detail: unknown }).detail);
    }

    if (err.code === "ECONNABORTED") {
      return "The request timed out. Try uploading fewer images at once.";
    }
    if (!err.response) {
      return "Could not reach the server. Please check your connection and try again.";
    }
    return `Something went wrong on the server (status ${err.response.status}). Please try again.`;
  }

  return "An unexpected error occurred. Please try again.";
}
