---
name: Fix Members Display Hex ID
overview: Sửa lỗi màn hình Members hiển thị ID hex thay vì tên user do `normalizeConversation` tạo placeholder members không có thông tin user (fullName, avatar...).
todos:
  - id: verify-api
    content: Xác nhận format response của GET /conversations/{id} từ backend
    status: pending
  - id: choose-approach
    content: "Chọn phương án fix (A: fetch từng user, B: API mới, C: hiển thị tạm)"
    status: pending
  - id: implement
    content: Implement fix theo phương án đã chọn
    status: pending
  - id: test
    content: Test lại flow Members screen
    status: pending
isProject: false
---

## Mục tiêu

Sửa lỗi màn hình "Members" trong chat group hiển thị ID hex (như `1f8f64...`) thay vì tên user. Nguyên nhân: `normalizeConversation` trong [conversation-normalize.helper.ts](apps/sgod-sam-v2/src/utils/helpers/conversation-normalize.helper.ts) tạo placeholder members với `_id` từ `userId` nhưng `fullName`, `avatarUrl` đều trống.

## Phân tích luồng

### Flow Register Enterprise → Members Screen

1. `RegisterEnterprise` → gọi `POST /sgod-auth/v1/enterprises/register` → nhận OTP → verify OTP → hiện alert → Login.
2. Login thành công → vào Home → tap vào group chat có sẵn → `ChatScreen`.
3. Tap menu → `View members` → navigate `MembersChat` với `conversationId`.
4. `ListMembersChatComponent` gọi `GET /sgod-chat/v1/conversations/{id}` → `normalizeConversation` → trả members chỉ có `_id`.

### Root cause

[apps/sgod-sam-v2/src/utils/helpers/conversation-normalize.helper.ts](apps/sgod-sam-v2/src/utils/helpers/conversation-normalize.helper.ts) dòng 66-96:

```typescript
function buildMemberPlaceholder(m: RawConversationMember, idx: number): StoreBaseUser {
  return {
    _id: m.userId || `member-${idx}`,
    fullName: { firstName: '', lastName: '' },  // TRỐNG
    avatarUrl: '',                                // TRỐNG
    // ...
  };
}
```

Vì API `GET /conversations/{id}` thực sự chỉ trả về `members` dạng `{ userId, tenantId, belongTo }` (không có thông tin chi tiết user), `normalizeConversation` đang "đoán" `_id` từ `userId` để tránh crash nhưng các field `fullName`, `avatarUrl` đều rỗng → UI render `_id` hex thay vì tên.

## Cách giải quyết đề xuất

### Phương án A: Fetch thông tin user từ auth-service (Recommended)

Sau khi lấy conversation, với mỗi `userId` trong `members`, gọi `GET /sgod-auth/v1/enterprise-users/{userId}` (đã có sẵn endpoint) để lấy fullName, avatarUrl.

**Ưu điểm**: Hiển thị đầy đủ tên + avatar
**Nhược điểm**: N+1 request, tốc độ chậm nếu group nhiều members

### Phương án B: Backend bổ sung API lấy danh sách user theo IDs

Thêm endpoint `GET /enterprise-users?ids=a,b,c` để lấy 1 lần nhiều users. Cần backend support.

### Phương án C: Hiển thị tạm thời dạng rút gọn

Hiển thị `_id.slice(0, 6)` thay vì toàn bộ hex. Không cần thay đổi logic lớn.

## TODO

- [ ] **[pending]** Xác nhận chính xác format response của `GET /sgod-chat/v1/conversations/{id}` từ backend
- [ ] **[pending]** Chọn phương án (A/B/C) theo ý sếp
- [ ] **[pending]** Implement fix theo phương án đã chọn
- [ ] **[pending]** Test lại flow Members screen

## Câu hỏi cần sếp quyết định

1. API `GET /conversations/{id}` thực sự trả về members format gì? Backend có support endpoint lấy nhiều users cùng lúc không?
2. Sếp muốn dùng phương án nào?