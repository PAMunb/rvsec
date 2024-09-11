package com.fdu.se.sootanalyze.model;

//TODO
public enum ListenerType {
	OnClickListener("setOnClickListener", "onClick", Event.CLICK),
	OnLongClickListener("setOnLongClickListener", "onLongClick", Event.LONG_CLICK),
	OnItemClickListener("setOnItemClickListener", "onItemClick", Event.CLICK),
	OnItemLongClickListener("setOnItemLongClickListener", "onItemLongClick", Event.LONG_CLICK),
	OnMenuItemClickListener("setOnMenuItemClickListener", "onMenuItemClick", Event.CLICK),
	OnScrollListener("setOnScrollListener", "onScroll", Event.SCROLL),
	OnDragListener("setOnDragListener", "onDrag", Event.DRAG),
	OnHoverListener("setOnHoverListener", "onHover", Event.HOVER),
	OnTouchListener("setOnTouchListener", "onTouch", Event.TOUCH);
//	OnItemSelectedListener; //TODO
//	TextWatcher
//	OnFocusChangeListener
//	OnGestureListener
//	OnEditorActionListener
//	CompoundButton.OnCheckedChangeListener: Acionado quando o estado de um CompoundButton (como um CheckBox ou RadioButton) é alterado.

	private String listernerMethod;
	private String eventCallback;
	private Event event;

	ListenerType(String listernerMethod, String eventCallback, Event event) {
		this.listernerMethod = listernerMethod;
		this.eventCallback = eventCallback;
		this.event = event;
	}

	public String getListernerMethod() {
		return listernerMethod;
	}

	public String getEventCallback() {
		return eventCallback;
	}

	public Event getEvent() {
		return event;
	}

//	public Set<ListenerEnum> getListenersByBaseEvent(Event event) {
//		Set<ListenerEnum> listeners = new HashSet<>();
//		for (ListenerEnum listenerEnum : values()) {
//			if(listenerEnum.getEvent() == event) {
//				listeners.add(listenerEnum);
//			}
//		}
//		return listeners;
//	}
//
//	public static Event getEvent(String listenerMethod) {
//		for (ListenerEnum listenerEnum : values()) {
//			if(listenerEnum.getListernerMethod().equals(listenerMethod)) {
//				return listenerEnum.getEvent();
//			}
//		}
//		return null;
//	}

//OK 	OnClickListener: Para eventos de clique.
//OK	OnLongClickListener: Para eventos de clique longo.
//	TextWatcher: Para monitorar mudanças de texto em um EditText.
//	OnFocusChangeListener: Para monitorar mudanças de foco.
//	OnItemSelectedListener: Para eventos de seleção em um Spinner.
//	OnGestureListener: Para capturar gestos.
//
//	OnClickListener: O listener mais comum, é acionado quando o botão é clicado. Permite executar ações como navegar para outra tela, exibir um diálogo ou realizar alguma operação.
//	TextView
//	OnClickListener: Assim como o botão, o TextView também pode ter um OnClickListener para responder a cliques. Isso é útil quando você quer que o texto seja clicável, como em um link.
//	OnLongClickListener: Acionado quando o usuário pressiona longamente sobre o texto. Pode ser usado para mostrar um menu de contexto ou outras ações específicas.
//	EditText
//	TextWatcher: Permite monitorar as mudanças no texto inserido pelo usuário. Você pode usar esse listener para validar a entrada, formatar o texto ou atualizar outras partes da interface com base no que foi digitado.
//	OnEditorActionListener: Acionado quando o usuário pressiona a tecla Enter ou um botão de ação no teclado. É útil para enviar formulários ou realizar ações específicas quando o usuário termina de digitar.
//	Spinner
//	OnItemSelectedListener: Acionado quando o usuário seleciona um item da lista do Spinner. Permite realizar ações como atualizar outros elementos da interface ou carregar dados adicionais.
//	OnNothingSelectedListener: Acionado quando nenhum item está selecionado no Spinner. Geralmente usado para limpar campos ou restaurar um estado inicial.
//	Exemplo prático (OnClickListener em um Button):
//
//		View.OnTouchListener: Acionado quando o usuário toca em qualquer parte da view.
//		View.OnFocusChangeListener: Acionado quando a view ganha ou perde o foco.
//		CompoundButton.OnCheckedChangeListener: Acionado quando o estado de um CompoundButton (como um CheckBox ou RadioButton) é alterado.
//		SeekBar.OnSeekBarChangeListener: Acionado quando o valor de um SeekBar é alterado.
//		Como Implementar Listeners:
//
//			OnClickListener: Acionado quando o usuário clica em um elemento (botão, texto, imagem, etc.).
//			OnLongClickListener: Acionado quando o usuário pressiona longamente um elemento.
//			TextWatcher: Monitora as mudanças em um campo de texto (EditText).
//			OnFocusChangeListener: Acionado quando um elemento ganha ou perde o foco.
//			OnItemSelectedListener: Acionado quando um item é selecionado em uma lista (Spinner, ListView).
//			OnGestureListener: Captura gestos mais complexos, como deslizar, pinçar e girar.
//			OnItemClickListener: Acionado quando um item em uma lista (ListView, RecyclerView) é clicado.
//			Como usar os listeners:

//
//	Listeners em Android: Uma Visão Geral Completa
//	Entendendo Listeners
//
//	Em Android, listeners são interfaces que permitem que componentes da interface do usuário (views) respondam a eventos do usuário, como cliques, toques longos, mudanças de texto, etc. Quando um evento ocorre, o método apropriado no listener é chamado, permitindo que você execute a lógica necessária.
//
//	A Completude da Lista: Um Desafio
//
//	É importante notar que a lista completa de listeners em Android é bastante extensa e pode variar dependendo da versão do Android e das bibliotecas externas utilizadas. Além disso, a criação de custom views e custom listeners é uma prática comum em desenvolvimento Android, o que torna a lista ainda mais dinâmica.
//
//	Uma Abordagem Prática
//
//	Em vez de fornecer uma lista exaustiva e potencialmente desatualizada, vamos explorar os principais tipos de listeners e como eles são usados nas views mais comuns. Essa abordagem permitirá que você entenda os conceitos fundamentais e aplique-os em seus projetos.
//
//	Principais Tipos de Listeners e Exemplos
//
//	OnClickListener:
//	Dispara quando um view é clicado.
//	Usado em: Button, ImageButton, TextView, etc.
//	OnLongClickListener:
//	Dispara quando um view é pressionado por um longo período.
//	Usado em: Button, ImageButton, TextView, etc.
//	OnTouchListener:
//	Dispara em diversos eventos de toque, como toque para baixo, toque para cima, movimento.
//	Usado em: View, ViewGroup, etc.
//	TextWatcher:
//	Dispara quando o texto em um EditText é alterado.
//	Usado em: EditText
//	OnItemClickListener:
//	Dispara quando um item em uma ListView ou GridView é clicado.
//	Usado em: ListView, GridView
//	OnItemLongClickListener:
//	Dispara quando um item em uma ListView ou GridView é pressionado por um longo período.
//	Usado em: ListView, GridView
//	SeekBar.OnSeekBarChangeListener:
//	Dispara quando o valor de um SeekBar é alterado.
//	Usado em: SeekBar
}
