import axios from "axios";

const API_BASE = "http://127.0.0.1:8000";

export async function gradeExam(list_of_images: File[], config: File) {
  const formData = new FormData();

  list_of_images.forEach((image) =>{
    formData.append("list_of_images", image);
  });
  
  formData.append("config_json", config);

  const response = await axios.post(`${API_BASE}/grade/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
    responseType:"blob",
  });

  return response.data;
}
