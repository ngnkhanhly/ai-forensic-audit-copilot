# 🎯 10/10 Demo Case Walkthrough

This document outlines the ideal demo scenario to showcase the full power of the **AI Forensic Audit Copilot**. Do not just upload a single invoice; upload a context group to trigger the Cross-Document Audit Engine.

## Step 1: Upload the Document Group
Load the following 5 files from the `demo_data/` folder into the system:

1. `contract_ABC_2026.pdf` (Master agreement with Vendor ABC, stipulating Net 30 payment terms).
2. `invoice_INV-001.pdf` (Legitimate first invoice from Vendor ABC for 25,000,000 VND).
3. `invoice_INV001_copy.pdf` (Fraudulent near-duplicate invoice for 25,000,000 VND, submitted a day later).
4. `purchase_order_PO-889.pdf` (Valid PO attached to the first invoice).
5. `payment_history.csv` (Historical payments showing previous clearing of POs).

## Step 2: Query the Agent
In the LangGraph Agent Workspace, ask the following question:
> *"Kiểm tra vendor ABC có dấu hiệu gian lận hoặc rủi ro thanh toán nào không dựa trên các chứng từ mới tải lên?"*

## Step 3: Observe the Forensic Output
The system should bypass simple extraction and generate a highly detailed **Fraud Case Report**:

```text
[CRITICAL ALERT] Risk Score: 89/100 - Action Required: BLOCK PAYMENT

Phát hiện 3 dấu hiệu rủi ro nghiêm trọng liên quan đến Vendor ABC:

1. Trùng lặp hóa đơn mờ (Near-Duplicate Detected):
   - Hóa đơn INV-001 và INV001_copy trùng khớp 100% số tiền (25,000,000 VND) và thông tin vendor.
   - Tên số hóa đơn bị chỉnh sửa ký tự đặc biệt (INV-001 so với INV001_copy).
   -> Rủi ro thanh toán lặp: 25,000,000 VND.

2. Sai lệch kỳ hạn thanh toán (Contract Term Mismatch):
   - Hóa đơn INV-001 yêu cầu thanh toán trong vòng 7 ngày (Net 7).
   - Hợp đồng contract_ABC_2026.pdf quy định kỳ hạn thanh toán là 30 ngày (Net 30).
   -> Vendor đang cố gắng rút ngắn thời gian công nợ thêm 23 ngày.

3. Thiếu Đơn đặt hàng (Missing PO Reference):
   - Hóa đơn giả mạo INV001_copy không đính kèm mã đơn đặt hàng hợp lệ trong hệ thống.

Khuyến nghị: Hệ thống đã chuyển trạng thái 2 hóa đơn này sang BLOCKED. Đề nghị Kế toán trưởng không ký duyệt thanh toán.
```
