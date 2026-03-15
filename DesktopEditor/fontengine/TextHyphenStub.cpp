#include "./TextHyphen.h"

namespace NSHyphen
{
	class CEngine_private
	{
	};

	CEngine::CEngine()
	{
		m_internal = new CEngine_private();
	}

	CEngine::~CEngine()
	{
		delete m_internal;
	}

	void CEngine::Init(const std::wstring& directory)
	{
		(void)directory;
	}

	void CEngine::SetCacheSize(const int& size)
	{
		(void)size;
	}

	int CEngine::LoadDictionary(const int& lang)
	{
		(void)lang;
		return 1;
	}

	int CEngine::LoadDictionary(const int& lang, const unsigned char* data, const unsigned int& data_len)
	{
		(void)lang;
		(void)data;
		(void)data_len;
		return 1;
	}

	bool CEngine::IsDictionaryExist(const int& lang)
	{
		for (int i = 0; i < NSTextLanguages::DictionaryRec_count; ++i)
		{
			if (lang == NSTextLanguages::Dictionaries[i].m_lang)
				return true;
		}
		return false;
	}

	char* CEngine::Process(const int& lang, const char* word, const int& len)
	{
		(void)lang;
		(void)word;
		(void)len;
		return NULL;
	}
}
