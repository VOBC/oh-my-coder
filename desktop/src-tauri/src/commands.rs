use crate::types::*;
use reqwest::header::{HeaderMap, HeaderValue};
use tauri::State;

/// 提交任务到 omc server
#[tauri::command]
pub async fn submit_task(
    state: State<'_, AppState>,
    prompt: String,
    metadata: Option<std::collections::HashMap<String, String>>,
) -> Result<TaskResponse, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let client = state.ensure_client()?;
    let url = format!("{}/api/v1/run", config.base_url());

    let mut headers = HeaderMap::new();
    headers.insert("Content-Type", HeaderValue::from_static("application/json"));
    if let Some(ref key) = config.api_key {
        headers.insert("X-API-Key", HeaderValue::from_str(key).map_err(|e| e.to_string())?);
    }

    let body = RunRequest { prompt, metadata };
    let resp = client
        .post(&url)
        .headers(headers)
        .json(&body)
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    if !resp.status().is_success() {
        let status = resp.status().as_u16();
        let text = resp.text().await.unwrap_or_default();
        return Err(format!("Server 错误 {}: {}", status, text));
    }

    resp.json().await.map_err(|e| format!("解析响应失败: {}", e))
}

/// 查询任务状态
#[tauri::command]
pub async fn get_task_status(
    state: State<'_, AppState>,
    task_id: String,
) -> Result<TaskResponse, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let client = state.ensure_client()?;
    let url = format!("{}/api/v1/status/{}", config.base_url(), task_id);

    let mut headers = HeaderMap::new();
    if let Some(ref key) = config.api_key {
        headers.insert("X-API-Key", HeaderValue::from_str(key).map_err(|e| e.to_string())?);
    }

    let resp = client
        .get(&url)
        .headers(headers)
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    if resp.status().as_u16() == 404 {
        return Err("任务不存在".to_string());
    }

    resp.json().await.map_err(|e| format!("解析响应失败: {}", e))
}

/// 获取任务结果
#[tauri::command]
pub async fn get_task_result(
    state: State<'_, AppState>,
    task_id: String,
) -> Result<TaskResult, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let client = state.ensure_client()?;
    let url = format!("{}/api/v1/result/{}", config.base_url(), task_id);

    let mut headers = HeaderMap::new();
    if let Some(ref key) = config.api_key {
        headers.insert("X-API-Key", HeaderValue::from_str(key).map_err(|e| e.to_string())?);
    }

    let resp = client
        .get(&url)
        .headers(headers)
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    match resp.status().as_u16() {
        404 => Err("任务不存在".to_string()),
        202 => Err("任务尚未完成".to_string()),
        _ => resp.json().await.map_err(|e| format!("解析响应失败: {}", e)),
    }
}

/// 列出所有任务
#[tauri::command]
pub async fn list_tasks(
    state: State<'_, AppState>,
    limit: Option<u32>,
) -> Result<TaskListResponse, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let client = state.ensure_client()?;
    let limit = limit.unwrap_or(50);
    let url = format!("{}/api/v1/tasks?limit={}", config.base_url(), limit);

    let mut headers = HeaderMap::new();
    if let Some(ref key) = config.api_key {
        headers.insert("X-API-Key", HeaderValue::from_str(key).map_err(|e| e.to_string())?);
    }

    let resp = client
        .get(&url)
        .headers(headers)
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    resp.json().await.map_err(|e| format!("解析响应失败: {}", e))
}

/// 删除任务
#[tauri::command]
pub async fn delete_task(
    state: State<'_, AppState>,
    task_id: String,
) -> Result<bool, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let client = state.ensure_client()?;
    let url = format!("{}/api/v1/tasks/{}", config.base_url(), task_id);

    let mut headers = HeaderMap::new();
    if let Some(ref key) = config.api_key {
        headers.insert("X-API-Key", HeaderValue::from_str(key).map_err(|e| e.to_string())?);
    }

    let resp = client
        .delete(&url)
        .headers(headers)
        .send()
        .await
        .map_err(|e| format!("请求失败: {}", e))?;

    Ok(resp.status().is_success())
}

/// 更新 server 配置
#[tauri::command]
pub async fn update_config(
    state: State<'_, AppState>,
    host: String,
    port: u16,
    api_key: Option<String>,
) -> Result<(), String> {
    let mut config = state.config.lock().map_err(|e| e.to_string())?;
    config.host = host;
    config.port = port;
    config.api_key = api_key;
    Ok(())
}

/// 获取当前配置
#[tauri::command]
pub async fn get_config(state: State<'_, AppState>) -> Result<ServerConfig, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    Ok(config.clone())
}

/// 检查 server 连接状态
#[tauri::command]
pub async fn check_server_health(state: State<'_, AppState>) -> Result<bool, String> {
    let config = state.config.lock().map_err(|e| e.to_string())?;
    let client = state.ensure_client()?;
    let url = format!("{}/health", config.base_url());

    let resp = client
        .get(&url)
        .send()
        .await
        .map_err(|e| format!("无法连接: {}", e))?;

    Ok(resp.status().is_success())
}
