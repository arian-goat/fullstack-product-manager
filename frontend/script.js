// آدرس پایه API بک‌اند شما
// برای توسعه محلی:
const API_BASE_URL = 'http://127.0.0.1:5000'; 

// برای دپلوی (بعدا این خط را جایگزین خط بالا کنید و لینک Heroku خود را قرار دهید):
// const API_BASE_URL = 'https://your-heroku-backend-app.herokuapp.com'; 

// --- گرفتن رفرنس به عناصر HTML ---
const addProductForm = document.getElementById('addProductForm');
const productNameInput = document.getElementById('productName');
const productDescriptionInput = document.getElementById('productDescription');
const productPriceInput = document.getElementById('productPrice');
const formMessageDiv = document.getElementById('formMessage');
const productsContainer = document.getElementById('productsContainer');
const listMessageDiv = document.getElementById('listMessage');

// عناصر مربوط به جستجو
const searchQueryInput = document.getElementById('searchQuery');
const searchButton = document.getElementById('searchButton');
const clearSearchButton = document.getElementById('clearSearchButton');

// عناصر مربوط به مودال ویرایش
const editProductModal = document.getElementById('editProductModal');
const closeButton = document.querySelector('.close-button');
const editProductForm = document.getElementById('editProductForm');
const editProductIdInput = document.getElementById('editProductId');
const editProductNameInput = document.getElementById('editProductName');
const editProductDescriptionInput = document.getElementById('editProductDescription');
const editProductPriceInput = document.getElementById('editProductPrice');
const editFormMessageDiv = document.getElementById('editFormMessage');


// --- توابع کمکی برای نمایش پیام‌ها ---
function showMessage(element, message, type) {
    element.textContent = message;
    element.className = `message ${type}`;
    element.style.display = 'block';
    setTimeout(() => {
        element.style.display = 'none';
    }, 3000);
}

// --- تابع برای دریافت و نمایش محصولات از API (با قابلیت جستجو) ---
async function fetchProducts(searchQuery = '') {
    productsContainer.innerHTML = '<p class="loading-message">در حال بارگذاری محصولات...</p>';
    listMessageDiv.style.display = 'none';

    let url = `${API_BASE_URL}/products`;
    if (searchQuery) {
        url += `?search=${encodeURIComponent(searchQuery)}`; // اضافه کردن پارامتر جستجو
        clearSearchButton.style.display = 'inline-block'; // نمایش دکمه پاک کردن جستجو
    } else {
        clearSearchButton.style.display = 'none'; // مخفی کردن دکمه پاک کردن جستجو
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            // در صورت خطای HTTP (مثل 404, 500 و ...)
            const errorData = await response.json().catch(() => ({error: 'خطای ناشناخته از سرور.'}));
            throw new Error(`HTTP error! Status: ${response.status} - ${errorData.error || response.statusText}`);
        }
        const data = await response.json();

        productsContainer.innerHTML = '';

        if (data.products && data.products.length > 0) {
            data.products.forEach(product => {
                const productCard = document.createElement('div');
                productCard.className = 'product-card';
                productCard.dataset.productId = product.id;

                productCard.innerHTML = `
                    <h3>${product.name}</h3>
                    <p>${product.description || 'توضیحات ندارد.'}</p>
                    <p class="price">${product.price.toLocaleString('fa-IR')} تومان</p>
                    <div class="actions">
                        <button class="edit-button" data-id="${product.id}">ویرایش</button>
                        <button class="delete-button" data-id="${product.id}">حذف</button>
                    </div>
                `;
                productsContainer.appendChild(productCard);
            });
            // افزودن شنونده رویداد به دکمه‌های حذف و ویرایش
            document.querySelectorAll('.delete-button').forEach(button => {
                button.addEventListener('click', handleDeleteProduct);
            });
            document.querySelectorAll('.edit-button').forEach(button => {
                button.addEventListener('click', handleEditProduct);
            });
        } else {
            productsContainer.innerHTML = '<p class="no-products-message">هیچ محصولی برای نمایش وجود ندارد.</p>';
        }
    } catch (error) {
        console.error('Error fetching products:', error);
        productsContainer.innerHTML = `<p class="no-products-message error">خطا در بارگذاری محصولات: ${error.message}. لطفا سرور را بررسی کنید.</p>`;
        showMessage(listMessageDiv, `خطا در بارگذاری محصولات: ${error.message}`, 'error');
    }
}

// --- تابع برای افزودن محصول جدید ---
addProductForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const productName = productNameInput.value.trim();
    const productDescription = productDescriptionInput.value.trim();
    const productPrice = parseFloat(productPriceInput.value);

    if (!productName || isNaN(productPrice) || productPrice <= 0) {
        showMessage(formMessageDiv, 'لطفا نام و قیمت معتبر وارد کنید.', 'error');
        return;
    }

    const productData = {
        name: productName,
        description: productDescription,
        price: productPrice
    };

    try {
        const response = await fetch(`${API_BASE_URL}/products`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(productData)
        });

        const data = await response.json();

        if (response.ok) { // بررسی کد وضعیت HTTP (200-299)
            showMessage(formMessageDiv, data.message, 'success');
            addProductForm.reset();
            fetchProducts();
        } else {
            // نمایش پیام خطای خاص از سرور (مثلاً نام تکراری)
            showMessage(formMessageDiv, data.error || 'خطا در افزودن محصول.', 'error');
        }
    } catch (error) {
        console.error('Error adding product:', error);
        showMessage(formMessageDiv, 'خطا در ارتباط با سرور. (آیا سرور بک‌اند در حال اجراست؟)', 'error');
    }
});

// --- تابع برای حذف محصول ---
async function handleDeleteProduct(event) {
    const productId = event.target.dataset.id;

    if (!confirm('آیا مطمئن هستید که می‌خواهید این محصول را حذف کنید؟ این عمل قابل بازگشت نیست.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/products/${productId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (response.ok) {
            showMessage(listMessageDiv, data.message, 'success');
            fetchProducts();
        } else {
            showMessage(listMessageDiv, data.error || 'خطا در حذف محصول.', 'error');
        }
    } catch (error) {
        console.error('Error deleting product:', error);
        showMessage(listMessageDiv, 'خطا در ارتباط با سرور هنگام حذف.', 'error');
    }
}

// --- توابع مربوط به جستجو ---
searchButton.addEventListener('click', () => {
    const query = searchQueryInput.value.trim();
    fetchProducts(query);
});

searchQueryInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        const query = searchQueryInput.value.trim();
        fetchProducts(query);
    }
});

clearSearchButton.addEventListener('click', () => {
    searchQueryInput.value = ''; // پاک کردن کادر جستجو
    fetchProducts(); // نمایش همه محصولات
});


// --- توابع مربوط به ویرایش محصول (Modal) ---
async function handleEditProduct(event) {
    const productId = event.target.dataset.id;
    editProductIdInput.value = productId; // ذخیره ID در فیلد مخفی مودال

    try {
        const response = await fetch(`${API_BASE_URL}/products/${productId}`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({error: 'خطای ناشناخته از سرور.'}));
            throw new Error(`HTTP error! Status: ${response.status} - ${errorData.error || response.statusText}`);
        }
        const product = await response.json();

        // پر کردن فرم مودال با اطلاعات محصول
        editProductNameInput.value = product.name;
        editProductDescriptionInput.value = product.description;
        editProductPriceInput.value = product.price;

        editFormMessageDiv.style.display = 'none'; // مخفی کردن پیام‌های قبلی مودال
        editProductModal.classList.add('show'); // نمایش مودال با کلاس 'show'
    } catch (error) {
        console.error('Error fetching product for edit:', error);
        showMessage(listMessageDiv, `خطا در بارگذاری اطلاعات محصول برای ویرایش: ${error.message}`, 'error');
    }
}

// بستن مودال با دکمه X
closeButton.addEventListener('click', () => {
    editProductModal.classList.remove('show');
});

// بستن مودال با کلیک بیرون از محتوا
window.addEventListener('click', (event) => {
    if (event.target === editProductModal) {
        editProductModal.classList.remove('show');
    }
});


// ارسال فرم ویرایش محصول
editProductForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const productId = editProductIdInput.value;
    const updatedProductData = {
        name: editProductNameInput.value.trim(),
        description: editProductDescriptionInput.value.trim(),
        price: parseFloat(editProductPriceInput.value)
    };

    if (!updatedProductData.name || isNaN(updatedProductData.price) || updatedProductData.price <= 0) {
        showMessage(editFormMessageDiv, 'لطفا نام و قیمت معتبر وارد کنید.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/products/${productId}`, {
            method: 'PUT', // متد HTTP برای به‌روزرسانی
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedProductData)
        });

        const data = await response.json();

        if (response.ok) {
            showMessage(editFormMessageDiv, data.message, 'success');
            editProductModal.classList.remove('show'); // بستن مودال
            fetchProducts(); // بارگذاری مجدد لیست
        } else {
            showMessage(editFormMessageDiv, data.error || 'خطا در به‌روزرسانی محصول.', 'error');
        }
    } catch (error) {
        console.error('Error updating product:', error);
        showMessage(editFormMessageDiv, 'خطا در ارتباط با سرور هنگام به‌روزرسانی.', 'error');
    }
});


// --- بارگذاری محصولات هنگام بارگذاری اولیه صفحه ---
document.addEventListener('DOMContentLoaded', () => {
    fetchProducts();
});


// --- بارگذاری محصولات هنگام بارگذاری اولیه صفحه ---
document.addEventListener('DOMContentLoaded', () => {
    fetchProducts();
});