from kiwipiepy import Kiwi
import re

class SpacingFixer:
    def __init__(self):
        # Kiwi 형태소 분석기 초기화
        self.kiwi = Kiwi()
        
        # 1. 합성명사/고유명사 보호를 위한 사용자 사전 등록
        # 금융/공시 도메인 전문 용어 및 요구사항 예시의 단어들
        protected_terms = [
            "투자신탁", "집합투자기구", "수익증권", "법령", "투자대상", "환매청구접수",
            "총보수･비용", "기타비용", "순자산", "연평잔액", "차감전", "고위험자산",
            "상장지수집합투자기구", "운용전문인력", "성과보수", "집합투자증권", "이자율변동",
            "가격변동", "투자증권"
        ]
        for term in protected_terms:
            self.kiwi.add_user_word(term, "NNP", 10)
            
    def _normalize(self, input_data):
        is_list = isinstance(input_data, list)
        if is_list:
            # 리스트인 경우 모든 요소를 공백 없이 합침 (잘린 단어 복구)
            text = "".join(str(item) for item in input_data)
        else:
            # 문자열인 경우 기존 공백 제거 (잘못된 공백 제거)
            text = input_data.replace(" ", "")
        return text, is_list

    def fix(self, input_data):
        text, is_list = self._normalize(input_data)
        
        # Kiwi 형태소 분석
        tokens = self.kiwi.tokenize(text)
        
        result_text = ""
        for i, token in enumerate(tokens):
            form = token.form
            tag = token.tag
            
            if i == 0:
                result_text += form
            elif tag.startswith('J') or tag.startswith('E') or tag.startswith('X'):
                # 조사(J), 어미(E), 접미사(X)는 앞 단어에 붙임
                result_text += form
            elif tag == 'VCP': # 서술격 조사 '이' (예: ~이다)
                result_text += form
            elif form in [',', '.', '!', '?', ')', ']', '}', '>', '･', ':', ';']:
                # 문장 부호 및 닫는 괄호는 앞 토큰에 붙임
                result_text += form
            elif i > 0 and tokens[i-1].form in ['(', '[', '{', '<']:
                # 여는 괄호 다음은 붙임
                result_text += form
            elif tag == 'SN': # 숫자인 경우
                # 앞 토큰이 숫자면 붙임 (예: 8 0% -> 80%)
                if i > 0 and tokens[i-1].tag == 'SN':
                    result_text += form
                elif i > 0 and tokens[i-1].form == ',': # 천단위 콤마 대응
                    result_text += form
                elif i > 0 and tokens[i-1].form == '제': # '제' 뒤의 숫자 붙임
                    result_text += form
                else:
                    result_text += " " + form
            elif form in ['조', '항'] and i > 0 and tokens[i-1].tag == 'SN':
                # 숫자 뒤의 '조', '항'은 붙임
                result_text += form
            elif tag == 'SF': # 마침표 등 문장 부호 (Kiwi 태그 기준)
                 result_text += form
            elif tag == 'SY' and form in ['/', '･']: # 특수 기호
                 result_text += form
            else:
                # 그 외에는 띄어쓰기 수행
                result_text += " " + form
        
        # 사후 보정
        # 1. 숫자와 % 및 좌 단위 붙임
        result_text = re.sub(r'(\d)\s+([%좌])', r'\1\2', result_text)
        # 2. "법 제N조" 패턴 보정
        # Kiwi가 '법제'로 붙이거나 '제110'을 '제 110'으로 띄우는 경우 대응
        result_text = re.sub(r'법제\s*(\d)', r'법 제\1', result_text)
        result_text = re.sub(r'제\s+(\d+)', r'제\1', result_text)
        result_text = re.sub(r'(\d+)\s+([조항])', r'\1\2', result_text)
        
        if is_list:
            # 배열로 요청받은 경우 split하여 반환
            return result_text.split()
        return result_text.strip()

if __name__ == "__main__":
    fixer = SpacingFixer()
    
    examples = [
        ["투자대상", "의", "규모", "및", "유동성", "등을", "고려하여", "투자하고", "있으며,", "사후적으로", "투자대상의", "특성에", "맞게", "유동성", "위험과", "관", "련한", "내부", "관리", "..."],
        "투자자는 수익증권 입고 시점을 사 전에 점검하여 주시기 바랍니다.",
        ["수", "익자가", "당해", "환매청구접수의", "취소를", "하지", "아니하였을", "경우"],
        "총보수･비용 비율은 이 투자신탁에서 지출되는 보수와 기타비용 총액을 순자산 연평잔액(보수 및 비 용 차감전 기준)으로 나누어 산출합니다.",
        "고위험자산에 8 0%이상 투자하는 집합투자기구",
        ["기준일", "현재", "동", "운용전문인력이", "운용", "중인", "성과보수가", "약정된", "집합투자기구는", "없습니다."],
        "법 제110조에 의하여 신탁회사가 발행한 수익증권, 법 제9조 제21항의 규정에 의한 집합투자증권 및 법 제234조의 규정에 의한 상장지수집합투자기구 집합투자증권(이와 유사한 것으로 서 외국 법령에 따라 발행된 것을 포함)",
        "투자증권의 가격변동, 이자율변동 등 기타 거시경제",
        "금번 결산배당은 세제개편과 예상 배당재원을 감안, 정기 분기배당 금에 1.3조원을 추 가하여 총 3.75조원으로 이사 회가 정함."
    ]

    for i, ex in enumerate(examples, 1):
        print(f"Example {i} I: {ex}")
        result = fixer.fix(ex)
        print(f"Example {i} O: {result}")
        print("-" * 30)
